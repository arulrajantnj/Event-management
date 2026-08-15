from datetime import datetime
from io import BytesIO

import pandas as pd
from flask import Blueprint, redirect, render_template, request, send_file, session, url_for
from werkzeug.security import generate_password_hash

from excel_imports import read_import_file, workbook_response
from models import db
from student_models import (CustomRegistrationQuestion, RegistrationSetting, Student,
                            StudentAuditLog, StudentRegistrationAnswer)
from student_registration import DEFAULT_FIELDS, audit, ensure_registration_settings, registration_number


admin_student_bp = Blueprint("admin_student", __name__)


def admin_required():
    return "admin" in session


def settings():
    ensure_registration_settings()
    return RegistrationSetting.query.order_by(RegistrationSetting.sort_order, RegistrationSetting.id).all()


@admin_student_bp.route("/admin/student-registration/settings", methods=["GET", "POST"])
def registration_settings():
    if not admin_required(): return redirect(url_for("routes.login"))
    if request.method == "POST":
        for field in settings():
            field.enabled = f"enabled_{field.id}" in request.form
            field.required = f"required_{field.id}" in request.form
            field.sort_order = request.form.get(f"sort_{field.id}", field.sort_order, type=int) or 0
        db.session.commit()
        return redirect(url_for("admin_student.registration_settings", saved=1))
    return render_template("admin/registration_settings.html", fields=settings())


@admin_student_bp.route("/admin/student-registration/questions", methods=["GET", "POST"])
def custom_questions():
    if not admin_required(): return redirect(url_for("routes.login"))
    if request.method == "POST":
        label = request.form.get("label", "").strip()
        field_name = request.form.get("field_name", "").strip().lower().replace(" ", "_")
        if label and field_name and not CustomRegistrationQuestion.query.filter_by(field_name=field_name).first():
            db.session.add(CustomRegistrationQuestion(label=label, field_name=field_name, question_type=request.form.get("question_type", "text"), placeholder=request.form.get("placeholder", "").strip(), default_value=request.form.get("default_value", "").strip(), options=request.form.get("options", "").strip(), required="required" in request.form, is_active="is_active" in request.form, sort_order=request.form.get("sort_order", 0, type=int) or 0))
            db.session.commit()
        return redirect(url_for("admin_student.custom_questions"))
    questions = CustomRegistrationQuestion.query.order_by(CustomRegistrationQuestion.sort_order, CustomRegistrationQuestion.id).all()
    return render_template("admin/custom_questions.html", questions=questions)


@admin_student_bp.route("/admin/student-registration/questions/<int:question_id>/delete", methods=["POST"])
def delete_question(question_id):
    if not admin_required(): return redirect(url_for("routes.login"))
    question = CustomRegistrationQuestion.query.get_or_404(question_id)
    db.session.delete(question); db.session.commit()
    return redirect(url_for("admin_student.custom_questions"))


@admin_student_bp.route("/admin/students")
def students():
    if not admin_required(): return redirect(url_for("routes.login"))
    query = Student.query
    search = request.args.get("search", "").strip()
    status = request.args.get("status", "").strip()
    student_class = request.args.get("student_class", "").strip()
    school = request.args.get("school", "").strip()
    if search: query = query.filter((Student.student_name.contains(search)) | (Student.username.contains(search)) | (Student.emis_no.contains(search)))
    if status: query = query.filter_by(approval_status=status)
    if student_class: query = query.filter_by(student_class=student_class)
    if school: query = query.filter(Student.school_name.contains(school))
    page = query.order_by(Student.registration_date.desc()).paginate(
        page=request.args.get("page", 1, type=int), per_page=25, error_out=False
    )
    counts = {value: Student.query.filter_by(approval_status=value).count() for value in ("pending", "approved", "rejected")}
    return render_template("admin/student_management.html", students=page, counts=counts, search=search, status=status, student_class=student_class, school=school)


@admin_student_bp.route("/admin/students/<int:student_id>/status", methods=["POST"])
def change_status(student_id):
    if not admin_required(): return redirect(url_for("routes.login"))
    student = Student.query.get_or_404(student_id)
    status = request.form.get("status")
    if status in {"approved", "rejected", "pending"}:
        student.approval_status = status
        student.rejection_reason = request.form.get("rejection_reason", "").strip() if status == "rejected" else ""
        student.admin_notes = request.form.get("admin_notes", "").strip()
        if status == "approved": student.approved_by, student.approved_date = session.get("admin", "Admin"), datetime.utcnow()
        audit(student, status, student.rejection_reason)
        db.session.commit()
    return redirect(url_for("admin_student.students"))


@admin_student_bp.route("/admin/students/bulk-status", methods=["POST"])
def bulk_status():
    if not admin_required(): return redirect(url_for("routes.login"))
    status = request.form.get("status")
    if status in {"approved", "rejected"}:
        for student in Student.query.filter(Student.id.in_(request.form.getlist("student_ids", type=int))).all():
            student.approval_status = status
            if status == "approved": student.approved_by, student.approved_date = session.get("admin", "Admin"), datetime.utcnow()
            audit(student, f"bulk_{status}")
        db.session.commit()
    return redirect(url_for("admin_student.students"))


@admin_student_bp.route("/admin/students/<int:student_id>/reset-password", methods=["POST"])
def reset_password(student_id):
    if not admin_required(): return redirect(url_for("routes.login"))
    student = Student.query.get_or_404(student_id); password = request.form.get("password", "")
    if len(password) >= 8 and password == request.form.get("confirm_password"):
        student.password_hash = generate_password_hash(password); audit(student, "password_reset"); db.session.commit()
    return redirect(url_for("admin_student.students"))


@admin_student_bp.route("/admin/students/reset-password", methods=["POST"])
def reset_password_from_list():
    if not admin_required(): return redirect(url_for("routes.login"))
    student = Student.query.get_or_404(request.form.get("student_id", type=int))
    password = request.form.get("password", "")
    if len(password) >= 8 and password == request.form.get("confirm_password"):
        student.password_hash = generate_password_hash(password)
        audit(student, "password_reset")
        db.session.commit()
        return redirect(url_for("admin_student.students", password_reset=1))
    return redirect(url_for("admin_student.students", password_error=1))


@admin_student_bp.route("/admin/students/export.xlsx")
def export_students():
    if not admin_required(): return redirect(url_for("routes.login"))
    questions = CustomRegistrationQuestion.query.order_by(CustomRegistrationQuestion.sort_order).all()
    rows = []
    for student in Student.query.order_by(Student.registration_date.desc()).all():
        row = {"Registration No": student.registration_no, "Student Name": student.student_name, "Class": student.student_class, "Section": student.section, "EMIS No": student.emis_no, "UDISE No": student.udise_no, "School Name": student.school_name, "Block": student.school_block, "Management": student.school_management, "Mobile": student.mobile, "Medium": student.medium, "Username": student.username, "Status": student.approval_status, "Registration Date": student.registration_date}
        answer_map = {answer.question_id: answer.value for answer in student.answers}
        row.update({question.label: answer_map.get(question.id, "") for question in questions}); rows.append(row)
    output = BytesIO(); pd.DataFrame(rows).to_excel(output, index=False); output.seek(0)
    return send_file(output, as_attachment=True, download_name="students.xlsx", mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@admin_student_bp.route("/admin/students/import", methods=["POST"])
def import_students():
    if not admin_required(): return redirect(url_for("routes.login"))
    try: frame = read_import_file(request.files.get("student_file"))
    except (ValueError, AttributeError): return redirect(url_for("admin_student.students", import_error=1))
    created = 0
    for _, row in frame.iterrows():
        username = str(row.get("username", "")).strip(); password = str(row.get("password", "")).strip(); emis = str(row.get("emis_no", "")).strip(); mobile = str(row.get("mobile", "")).strip()
        if not username or not password or Student.query.filter((Student.username == username) | (Student.emis_no == emis) | (Student.mobile == mobile)).first(): continue
        student = Student(registration_no=registration_number(), student_name=str(row.get("student_name", "")).strip(), student_class=str(row.get("class", row.get("student_class", ""))).strip(), section=str(row.get("section", "")).strip(), emis_no=emis, udise_no=str(row.get("udise_no", "")).strip(), school_name=str(row.get("school_name", "")).strip(), mobile=mobile, medium=str(row.get("medium", "")).strip(), username=username, password_hash=generate_password_hash(password), approval_status=str(row.get("approval_status", "approved")).strip().lower() or "approved")
        db.session.add(student); db.session.flush(); audit(student, "imported"); created += 1
    db.session.commit()
    return redirect(url_for("admin_student.students", import_created=created))


@admin_student_bp.route("/admin/students/template.xlsx")
def student_template():
    if not admin_required(): return redirect(url_for("routes.login"))
    output, filename = workbook_response(["student_name", "class", "section", "emis_no", "udise_no", "school_name", "mobile", "medium", "username", "password", "approval_status"], ["Required: student_name, emis_no, mobile, username, password.", "Use unique EMIS, mobile, and username values.", "approval_status defaults to approved when blank."], "student_import_template.xlsx")
    return send_file(output, as_attachment=True, download_name=filename, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
