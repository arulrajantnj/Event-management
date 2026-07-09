from collections import Counter, defaultdict
from datetime import datetime

from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError

from attendance_utils import extract_registration_id, now_utc, serialize_dt, today_date
from models import Attendance, AttendanceLog, Event, Participant, db


def admin_name(session):
    if session.get("admin"):
        return "Admin"
    if session.get("scanner_user_name"):
        return f"Scanner: {session.get('scanner_user_name')}"
    return "Unknown"


def participant_photo_url(participant):
    if not participant or not participant.photo:
        return ""
    photo = participant.photo.replace("\\", "/")
    if photo.startswith("static/"):
        return "/" + photo
    return "/static/uploads/" + photo


def participant_payload(participant, attendance=None):
    return {
        "id": participant.id,
        "reg_id": participant.reg_id,
        "teacher_name": participant.teacher_name,
        "mobile": participant.mobile,
        "email": participant.email,
        "designation": participant.designation,
        "subject": participant.subject,
        "school_name": participant.school_name,
        "school_area": participant.school_area,
        "block": participant.block,
        "photo_url": participant_photo_url(participant),
        "event_id": participant.event_id,
        "event_name": participant.event.name if participant.event else "",
        "attendance_status": attendance.status if attendance else "Absent",
        "attendance_time": serialize_dt(attendance.attendance_time) if attendance else "",
        "attendance_method": attendance.method if attendance else "",
    }


def log_activity(action, status="", method="", participant=None, event_id=None,
                 scan_text="", message="", admin_user="", ip_address=""):
    log = AttendanceLog(
        participant_id=participant.id if participant else None,
        event_id=event_id or (participant.event_id if participant else None),
        action=action,
        status=status,
        method=method,
        scan_text=(scan_text or "")[:2000],
        message=(message or "")[:255],
        admin_user=admin_user,
        ip_address=ip_address,
    )
    db.session.add(log)
    return log


def attendance_for_today(participant, date_value=None):
    date_value = date_value or today_date()
    return Attendance.query.filter_by(
        participant_id=participant.id,
        attendance_date=date_value
    ).first()


def find_participant_by_reg_id(reg_id, event_id=None):
    query = Participant.query.filter(func.upper(Participant.reg_id) == (reg_id or "").upper())
    if event_id:
        query = query.filter(Participant.event_id == event_id)
    return query.first()


def search_participants(term="", event_id=None, limit=25):
    term = (term or "").strip()
    query = Participant.query

    if event_id:
        query = query.filter(Participant.event_id == event_id)

    if term:
        like = f"%{term}%"
        query = query.filter(or_(
            Participant.reg_id.ilike(like),
            Participant.mobile.ilike(like),
            Participant.teacher_name.ilike(like),
            Participant.school_name.ilike(like),
        ))

    return query.order_by(Participant.teacher_name.asc()).limit(limit).all()


def mark_attendance(participant, method, admin_user, ip_address="", remarks=""):
    if not participant:
        return {
            "ok": False,
            "status": "Not Found",
            "message": "Participant Not Found",
            "participant": None,
        }

    existing = attendance_for_today(participant)
    if existing:
        log_activity(
            "Duplicate Attempt",
            status="Already Present",
            method=method,
            participant=participant,
            message="Duplicate attendance scan",
            admin_user=admin_user,
            ip_address=ip_address,
        )
        db.session.commit()
        return {
            "ok": True,
            "duplicate": True,
            "status": "Already Present",
            "message": "Already Present",
            "attendance": existing,
            "participant": participant_payload(participant, existing),
        }

    stamp = now_utc()
    attendance = Attendance(
        participant_id=participant.id,
        event_id=participant.event_id,
        attendance_date=stamp.date(),
        attendance_time=stamp,
        status="Present",
        method=method,
        remarks=remarks,
        marked_by=admin_user,
    )
    db.session.add(attendance)

    participant.is_present = True
    participant.attendance_marked_at = stamp

    log_activity(
        f"{method} Attendance",
        status="Present",
        method=method,
        participant=participant,
        message="Attendance marked successfully",
        admin_user=admin_user,
        ip_address=ip_address,
    )

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        existing = attendance_for_today(participant)
        return {
            "ok": True,
            "duplicate": True,
            "status": "Already Present",
            "message": "Already Present",
            "attendance": existing,
            "participant": participant_payload(participant, existing),
        }

    return {
        "ok": True,
        "duplicate": False,
        "status": "Present",
        "message": "Attendance Marked Successfully",
        "attendance": attendance,
        "participant": participant_payload(participant, attendance),
    }


def handle_qr_scan(scan_text, event_id, admin_user, ip_address=""):
    reg_id = extract_registration_id(scan_text)
    participant = find_participant_by_reg_id(reg_id, event_id) if reg_id else None

    if not participant:
        log_activity(
            "Invalid QR",
            status="Absent",
            method="QR",
            event_id=event_id,
            scan_text=scan_text,
            message="Participant Not Found",
            admin_user=admin_user,
            ip_address=ip_address,
        )
        db.session.commit()
        return {
            "ok": False,
            "status": "Absent",
            "message": "Participant Not Found",
            "reg_id": reg_id,
        }

    result = mark_attendance(participant, "QR", admin_user, ip_address)
    if result.get("attendance"):
        result["attendance_time"] = serialize_dt(result["attendance"].attendance_time)
        result.pop("attendance", None)
    return result


def handle_manual_mark(participant_id, admin_user, ip_address=""):
    participant = Participant.query.get(participant_id)
    result = mark_attendance(participant, "Manual", admin_user, ip_address)
    if result.get("attendance"):
        result["attendance_time"] = serialize_dt(result["attendance"].attendance_time)
        result.pop("attendance", None)
    return result


def event_options():
    return Event.query.order_by(Event.created_at.desc(), Event.id.desc()).all()


def attendance_query(event_id=None, status="present"):
    if status == "absent":
        present_ids = db.session.query(Attendance.participant_id).filter(
            Attendance.attendance_date == today_date()
        )
        query = Participant.query
        if event_id:
            query = query.filter(Participant.event_id == event_id)
        return query.filter(~Participant.id.in_(present_ids))

    query = Attendance.query.join(Participant)
    if event_id:
        query = query.filter(Attendance.event_id == event_id)
    return query.order_by(Attendance.attendance_time.desc())


def statistics(event_id=None):
    participant_query = Participant.query
    attendance_query_base = Attendance.query.filter(
        Attendance.attendance_date == today_date()
    )

    if event_id:
        participant_query = participant_query.filter(Participant.event_id == event_id)
        attendance_query_base = attendance_query_base.filter(Attendance.event_id == event_id)

    total = participant_query.count()
    present = attendance_query_base.count()
    absent = max(total - present, 0)
    qr_count = attendance_query_base.filter(Attendance.method == "QR").count()
    manual_count = attendance_query_base.filter(Attendance.method == "Manual").count()

    duplicate_query = AttendanceLog.query.filter(
        AttendanceLog.action == "Duplicate Attempt"
    )
    if event_id:
        duplicate_query = duplicate_query.filter(AttendanceLog.event_id == event_id)
    duplicate_count = duplicate_query.count()

    attendance_rows = attendance_query_base.join(Participant).all()
    hour_counts = Counter(row.attendance_time.strftime("%H:00") for row in attendance_rows)
    subject_counts = Counter((row.participant.subject or "Not Set") for row in attendance_rows)
    block_counts = Counter((row.participant.block or "Not Set") for row in attendance_rows)
    school_counts = Counter((row.participant.school_name or "Not Set") for row in attendance_rows)

    return {
        "total": total,
        "present": present,
        "absent": absent,
        "percentage": round((present / total) * 100, 2) if total else 0,
        "qr_count": qr_count,
        "manual_count": manual_count,
        "duplicate_count": duplicate_count,
        "by_hour": dict(sorted(hour_counts.items())),
        "by_subject": dict(subject_counts.most_common(10)),
        "by_block": dict(block_counts.most_common(10)),
        "by_school": dict(school_counts.most_common(10)),
    }


def recent_attendance(event_id=None, limit=12):
    query = Attendance.query.join(Participant)
    if event_id:
        query = query.filter(Attendance.event_id == event_id)
    return query.order_by(Attendance.attendance_time.desc()).limit(limit).all()


def duplicate_logs(event_id=None, limit=200):
    query = AttendanceLog.query.filter(AttendanceLog.action == "Duplicate Attempt")
    if event_id:
        query = query.filter(AttendanceLog.event_id == event_id)
    return query.order_by(AttendanceLog.created_at.desc()).limit(limit).all()
