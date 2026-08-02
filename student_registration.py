from datetime import datetime
import re

from flask import Blueprint, redirect, render_template, request, session, url_for
from werkzeug.security import generate_password_hash

from extensions import limiter
from models import db
from student_models import (CustomRegistrationQuestion, RegistrationSetting, Student,
                            StudentAuditLog, StudentRegistrationAnswer)


student_registration_bp = Blueprint("student_registration", __name__)

DEFAULT_FIELDS = [
    ("student_name", "Student Name", True), ("student_class", "Class", True),
    ("section", "Section", True), ("emis_no", "Student EMIS Number", True),
    ("udise_no", "School UDISE Number", True), ("school_name", "School Name", True),
    ("mobile", "Mobile Number", True), ("medium", "Medium", True),
    ("username", "Create Username", True), ("password", "Create Password", True),
]


def ensure_registration_settings():
    for position, (name, label, required) in enumerate(DEFAULT_FIELDS, start=1):
        if not RegistrationSetting.query.filter_by(field_name=name).first():
            db.session.add(RegistrationSetting(field_name=name, field_label=label, required=required, sort_order=position))
    db.session.commit()


def active_fields():
    ensure_registration_settings()
    return RegistrationSetting.query.filter_by(enabled=True).order_by(RegistrationSetting.sort_order, RegistrationSetting.id).all()


def audit(student, action, details=""):
    db.session.add(StudentAuditLog(student_id=student.id, action=action, details=details, actor=session.get("admin", "Student")))


def registration_number():
    prefix = f"REG{datetime.now().year}"
    latest = Student.query.filter(Student.registration_no.like(f"{prefix}%")).order_by(Student.id.desc()).first()
    sequence = int(latest.registration_no[-5:]) + 1 if latest and latest.registration_no[-5:].isdigit() else 1
    return f"{prefix}{sequence:05d}"


@student_registration_bp.route("/student/register", methods=["GET", "POST"])
@limiter.limit("5 per minute", methods=["POST"])
def register():
    fields = active_fields()
    questions = CustomRegistrationQuestion.query.filter_by(is_active=True).order_by(CustomRegistrationQuestion.sort_order, CustomRegistrationQuestion.id).all()
    errors = []
    if request.method == "POST":
        data = {field.field_name: request.form.get(field.field_name, "").strip() for field in fields}
        for field in fields:
            if field.required and not data[field.field_name]:
                errors.append(f"{field.field_label} is required.")
        if "password" in data and data.get("password") != request.form.get("confirm_password", ""):
            errors.append("Password and confirmation do not match.")
        if data.get("emis_no") and (not data["emis_no"].isdigit() or Student.query.filter_by(emis_no=data["emis_no"]).first()):
            errors.append("EMIS number must contain digits only and be unique.")
        if data.get("mobile") and (not re.fullmatch(r"\d{10}", data["mobile"]) or Student.query.filter_by(mobile=data["mobile"]).first()):
            errors.append("Mobile number must be a unique 10-digit number.")
        if data.get("username") and Student.query.filter_by(username=data["username"]).first():
            errors.append("Username already exists.")
        answers = {}
        for question in questions:
            value = request.form.getlist(f"custom_{question.id}") if question.question_type == "checkbox" else request.form.get(f"custom_{question.id}", "")
            value = ", ".join(value) if isinstance(value, list) else value.strip()
            if question.required and not value:
                errors.append(f"{question.label} is required.")
            answers[question.id] = value
        if not request.form.get("declaration"):
            errors.append("You must accept the declaration.")
        if not errors:
            student = Student(
                registration_no=registration_number(), student_name=data.get("student_name", ""),
                student_class=data.get("student_class"), section=data.get("section"), emis_no=data.get("emis_no"),
                udise_no=data.get("udise_no"), school_name=data.get("school_name"), mobile=data.get("mobile"),
                medium=data.get("medium"), username=data.get("username", ""), password_hash=generate_password_hash(data.get("password", "")),
            )
            db.session.add(student); db.session.flush()
            for question in questions:
                db.session.add(StudentRegistrationAnswer(student_id=student.id, question_id=question.id, value=answers[question.id]))
            audit(student, "registered")
            db.session.commit()
            return render_template("student/registration_success.html", student=student)
    return render_template("student/register.html", fields=fields, questions=questions, errors=errors)


@student_registration_bp.route("/student/login", methods=["GET", "POST"])
def login():
    return redirect(url_for("routes.exam_login"), code=307 if request.method == "POST" else 302)


@student_registration_bp.route("/student/dashboard")
def dashboard():
    student = db.session.get(Student, session.get("student_id"))
    if not student:
        return redirect(url_for("student_registration.login"))
    return render_template("student/dashboard.html", student=student)


@student_registration_bp.route("/student/logout")
def logout():
    session.pop("student_id", None)
    return redirect(url_for("routes.exam_login"))
