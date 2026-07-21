from functools import wraps
from datetime import datetime
from io import BytesIO, StringIO

import pandas as pd
from flask import (
    Blueprint,
    Response,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from werkzeug.security import check_password_hash, generate_password_hash
from extensions import limiter

from attendance_service import (
    admin_name,
    attendance_query,
    duplicate_logs,
    event_options,
    handle_manual_mark,
    handle_qr_scan,
    participant_payload,
    recent_attendance,
    search_participants,
    statistics,
)
from attendance_utils import serialize_dt
from models import ScannerUser, Participant, db


attendance_bp = Blueprint("attendance", __name__)


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "admin" not in session:
            return redirect(url_for("routes.login"))
        return view(*args, **kwargs)
    return wrapped


def json_admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "admin" not in session:
            return jsonify({"ok": False, "message": "Admin login required"}), 401
        return view(*args, **kwargs)
    return wrapped


def scanner_or_admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if session.get("admin") or session.get("scanner_user_id"):
            return view(*args, **kwargs)
        return redirect(url_for("attendance.scanner_login"))
    return wrapped


def json_scanner_or_admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if session.get("admin") or session.get("scanner_user_id"):
            return view(*args, **kwargs)
        return jsonify({"ok": False, "message": "Approved scanner login required"}), 401
    return wrapped


def selected_event_id():
    return request.values.get("event_id", type=int)


def payload_int(payload, key):
    if hasattr(payload, "getlist"):
        return payload.get(key, type=int)
    value = payload.get(key)
    try:
        return int(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def allowed_event_id(requested_event_id=None):
    scanner_event_id = session.get("scanner_event_id")
    if scanner_event_id:
        return int(scanner_event_id)
    return requested_event_id


@attendance_bp.route("/admin/attendance")
@attendance_bp.route("/admin/attendance/dashboard")
@admin_required
def dashboard():
    event_id = selected_event_id()
    return render_template(
        "admin/attendance/dashboard.html",
        events=event_options(),
        selected_event_id=event_id,
        stats=statistics(event_id),
        recent=recent_attendance(event_id),
    )


@attendance_bp.route("/admin/attendance/scanner")
@scanner_or_admin_required
def scanner():
    if session.get("scanner_user_id") and not session.get("admin"):
        return redirect(url_for("attendance.mobile_scanner"))

    return render_template(
        "admin/attendance/scanner.html",
        events=event_options(),
        selected_event_id=selected_event_id(),
    )


@attendance_bp.route("/attendance/scanner-login", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])
def scanner_login():
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        user = ScannerUser.query.filter_by(username=username).first()

        if (
            user
            and user.is_active
            and user.is_approved
            and check_password_hash(user.password_hash, password)
        ):
            session["scanner_user_id"] = user.id
            session["scanner_user_name"] = user.name
            session["scanner_event_id"] = user.event_id
            user.last_login_at = datetime.utcnow()
            db.session.commit()
            return redirect(url_for("attendance.mobile_scanner"))

        return render_template(
            "admin/attendance/scanner_login.html",
            error="Invalid login or scanner user is not approved by admin."
        )

    return render_template("admin/attendance/scanner_login.html")


@attendance_bp.route("/attendance/scanner-logout")
def scanner_logout():
    session.pop("scanner_user_id", None)
    session.pop("scanner_user_name", None)
    session.pop("scanner_event_id", None)
    return redirect(url_for("attendance.scanner_login"))


@attendance_bp.route("/attendance/mobile-scanner")
@scanner_or_admin_required
def mobile_scanner():
    return render_template(
        "admin/attendance/mobile_scanner.html",
        events=event_options(),
        selected_event_id=allowed_event_id(selected_event_id()),
        scanner_name=session.get("scanner_user_name", "Admin"),
        locked_event_id=session.get("scanner_event_id"),
    )


@attendance_bp.route("/admin/attendance/scanner-users", methods=["GET", "POST"])
@admin_required
def scanner_users():
    if request.method == "POST":
        user_id = request.form.get("user_id", type=int)
        action = request.form.get("action", "create")

        if action == "create":
            username = (request.form.get("username") or "").strip()
            password = request.form.get("password") or ""
            name = (request.form.get("name") or "").strip()
            event_id = request.form.get("event_id", type=int)

            if username and password and name:
                db.session.add(ScannerUser(
                    name=name,
                    username=username,
                    password_hash=generate_password_hash(password),
                    event_id=event_id,
                    is_approved=True,
                    is_active=True,
                    approved_by="Admin",
                    approved_at=datetime.utcnow(),
                ))
                db.session.commit()

        elif user_id:
            user = ScannerUser.query.get_or_404(user_id)
            if action == "approve":
                user.is_approved = True
                user.approved_by = "Admin"
                user.approved_at = datetime.utcnow()
            elif action == "toggle":
                user.is_active = not user.is_active
            elif action == "delete":
                db.session.delete(user)
            db.session.commit()

    users = ScannerUser.query.order_by(ScannerUser.created_at.desc()).all()
    return render_template(
        "admin/attendance/scanner_users.html",
        users=users,
        events=event_options(),
        selected_event_id=selected_event_id(),
    )


@attendance_bp.route("/admin/attendance/manual")
@admin_required
def manual():
    return render_template(
        "admin/attendance/manual.html",
        events=event_options(),
        selected_event_id=selected_event_id(),
    )


@attendance_bp.route("/admin/attendance/list")
@admin_required
def attendance_list():
    event_id = selected_event_id()
    rows = attendance_query(event_id).limit(1000).all()
    return render_template(
        "admin/attendance/attendance_list.html",
        events=event_options(),
        selected_event_id=event_id,
        rows=rows,
        mode="present",
    )


@attendance_bp.route("/admin/attendance/absent")
@admin_required
def absent_list():
    event_id = selected_event_id()
    rows = attendance_query(event_id, status="absent").order_by(
        Participant.teacher_name.asc()
    ).limit(1000).all()
    return render_template(
        "admin/attendance/attendance_list.html",
        events=event_options(),
        selected_event_id=event_id,
        rows=rows,
        mode="absent",
    )


@attendance_bp.route("/admin/attendance/duplicates")
@admin_required
def duplicate_scan_log():
    event_id = selected_event_id()
    return render_template(
        "admin/attendance/reports.html",
        events=event_options(),
        selected_event_id=event_id,
        logs=duplicate_logs(event_id),
        report_title="Duplicate Scan Log",
    )


@attendance_bp.route("/admin/attendance/reports")
@admin_required
def reports():
    event_id = selected_event_id()
    return render_template(
        "admin/attendance/attendance_reports.html",
        events=event_options(),
        selected_event_id=event_id,
        stats=statistics(event_id),
    )


@attendance_bp.route("/admin/attendance/settings")
@admin_required
def settings():
    return render_template(
        "admin/attendance/settings.html",
        events=event_options(),
        selected_event_id=selected_event_id(),
    )


@attendance_bp.route("/api/attendance/scan", methods=["POST"])
@limiter.limit("60 per minute")
@json_scanner_or_admin_required
def api_scan():
    payload = request.get_json(silent=True) or request.form
    event_id = allowed_event_id(payload_int(payload, "event_id"))
    result = handle_qr_scan(
        payload.get("scan_text", ""),
        event_id,
        admin_name(session),
        request.remote_addr or "",
    )
    return jsonify(result), 200 if result.get("ok") else 404


@attendance_bp.route("/api/attendance/manual", methods=["POST"])
@limiter.limit("30 per minute")
@json_admin_required
def api_manual():
    payload = request.get_json(silent=True) or request.form
    participant_id = payload_int(payload, "participant_id")
    result = handle_manual_mark(
        participant_id,
        admin_name(session),
        request.remote_addr or "",
    )
    return jsonify(result), 200 if result.get("ok") else 404


@attendance_bp.route("/api/attendance/search")
@json_scanner_or_admin_required
def api_search():
    event_id = allowed_event_id(request.args.get("event_id", type=int))
    participants = search_participants(
        request.args.get("q", ""),
        event_id=event_id,
        limit=30,
    )
    return jsonify({
        "ok": True,
        "participants": [participant_payload(item) for item in participants],
    })


@attendance_bp.route("/api/attendance/statistics")
@json_admin_required
def api_statistics():
    return jsonify({
        "ok": True,
        "statistics": statistics(request.args.get("event_id", type=int)),
    })


def export_rows(event_id=None, mode="present"):
    if mode == "absent":
        participants = attendance_query(event_id, status="absent").all()
        return [{
            "Registration Number": item.reg_id,
            "Teacher Name": item.teacher_name,
            "Mobile": item.mobile,
            "School": item.school_name,
            "Subject": item.subject,
            "Block": item.block,
            "Status": "Absent",
        } for item in participants]

    rows = attendance_query(event_id).all()
    return [{
        "Registration Number": row.participant.reg_id,
        "Teacher Name": row.participant.teacher_name,
        "Mobile": row.participant.mobile,
        "School": row.participant.school_name,
        "Subject": row.participant.subject,
        "Block": row.participant.block,
        "Attendance Time": serialize_dt(row.attendance_time),
        "Method": row.method,
        "Status": row.status,
        "Marked By": row.marked_by,
    } for row in rows]


@attendance_bp.route("/admin/attendance/export/<file_type>")
@admin_required
def export(file_type):
    event_id = request.args.get("event_id", type=int)
    mode = request.args.get("mode", "present")
    rows = export_rows(event_id, mode)
    filename = f"attendance_{mode}.{file_type}"

    if file_type == "csv":
        output = StringIO()
        pd.DataFrame(rows).to_csv(output, index=False)
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    if file_type == "xlsx":
        output = BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            pd.DataFrame(rows).to_excel(writer, index=False, sheet_name="Attendance")
        output.seek(0)
        return send_file(output, as_attachment=True, download_name=filename)

    if file_type == "pdf":
        output = BytesIO()
        pdf = canvas.Canvas(output, pagesize=A4)
        width, height = A4
        y = height - 40
        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawString(40, y, "Vandurai Events - Attendance Report")
        y -= 28
        pdf.setFont("Helvetica", 8)
        for row in rows[:500]:
            line = " | ".join(str(row.get(key, "")) for key in list(row.keys())[:6])
            pdf.drawString(40, y, line[:130])
            y -= 14
            if y < 40:
                pdf.showPage()
                pdf.setFont("Helvetica", 8)
                y = height - 40
        pdf.save()
        output.seek(0)
        return send_file(output, as_attachment=True, download_name=filename)

    return redirect(url_for("attendance.attendance_list"))
