from datetime import datetime
from functools import lru_cache
import json
import os
import re

from flask import Blueprint, current_app, jsonify, redirect, render_template, request, session, url_for
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


def first_value(data, *keys):
    for key in keys:
        value = data.get(key)
        if value not in (None, ""):
            return str(value).strip()
    return ""


def normalize_directory_column(value):
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")


@lru_cache(maxsize=4)
def load_school_directory(filename, modified_at):
    import pandas as pd

    try:
        directory = pd.read_excel(filename, dtype=object)
    except Exception as error:
        raise ValueError("School directory file could not be read.") from error

    columns = {normalize_directory_column(column): column for column in directory.columns}
    required_columns = {"udise_code", "school_name", "management", "block"}
    if not required_columns.issubset(columns):
        raise ValueError("School directory must contain UDISE_Code, School_Name, Management, and Block columns.")

    schools = {}
    for _, row in directory.iterrows():
        udise_no = first_value({"udise_code": row[columns["udise_code"]]}, "udise_code")
        school_name = first_value({"school_name": row[columns["school_name"]]}, "school_name")
        if not udise_no or not school_name:
            continue
        details = {
            normalize_directory_column(column): "" if row[column] is None else str(row[column]).strip()
            for column in directory.columns
        }
        schools[udise_no] = {
            "school_name": school_name,
            "block": first_value({"block": row[columns["block"]]}, "block"),
            "management": first_value({"management": row[columns["management"]]}, "management"),
            "details": details,
        }
    return schools


def fetch_school_details(udise_no):
    filename = current_app.config.get("SCHOOL_DIRECTORY_FILE", "")
    if not filename or not os.path.isfile(filename):
        return None, "School directory file is not available."
    try:
        schools = load_school_directory(filename, os.path.getmtime(filename))
    except ValueError as error:
        return None, str(error)
    school = schools.get(udise_no)
    if not school:
        return None, "No school was found for this UDISE number."
    return school, ""


@student_registration_bp.route("/student/school-lookup/<udise_no>")
@limiter.limit("30 per minute")
def school_lookup(udise_no):
    if not udise_no.isdigit():
        return jsonify({"error": "Enter a valid numeric UDISE number."}), 400

    school, error = fetch_school_details(udise_no)
    if error:
        status = 503 if "directory file" in error else 404
        return jsonify({"error": error}), status
    return jsonify({
        "school_name": school["school_name"],
        "block": school["block"],
        "management": school["management"],
    })


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
        school = None
        if data.get("udise_no"):
            school, school_error = fetch_school_details(data["udise_no"])
            if school_error:
                errors.append(school_error)
            elif "school_name" in data:
                data["school_name"] = school["school_name"]
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
                school_block=school["block"] if school else "",
                school_management=school["management"] if school else "",
                school_details=json.dumps(school["details"]) if school else "",
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
