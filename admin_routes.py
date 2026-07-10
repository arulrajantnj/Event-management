from flask import Blueprint, render_template, request, redirect, session, send_file, url_for
from models import (
    db,
    Event,
    EventField,
    ExamAnswer,
    ExamAttempt,
    ExamQuestion,
    ExamSubject,
    OnlineExam,
    Participant,
    ExamDutyAllocation,
    ExamDutyCenter,
    ExamDutyTeacher,
    Competition,
    CompetitionJudge,
    CompetitionRegistration,
)
from datetime import datetime
import math
from io import BytesIO
import json
import os
import pandas as pd
import re
import uuid
import random
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash
from attendance_service import mark_attendance as service_mark_attendance
from routes import generate_participant_code, registration_id_for_event


admin_bp = Blueprint("admin", __name__)

REGISTRATION_TYPE_CHOICES = [
    ("teacher", "Teachers"),
    ("student", "Students"),
    ("public", "Common Public"),
    ("no_registration", "No Registration Event"),
]

FIELD_TYPE_CHOICES = [
    ("text", "Text Entry"),
    ("textarea", "Paragraph"),
    ("select", "Drop Down"),
    ("email", "Email"),
    ("tel", "Mobile / Phone"),
    ("number", "Number"),
    ("date", "Date"),
]

ANSWER_OPTION_CHOICES = [
    ("A", "Option A"),
    ("B", "Option B"),
    ("C", "Option C"),
    ("D", "Option D"),
]

QUESTION_TYPE_CHOICES = [
    ("mcq", "Multiple Choice"),
    ("descriptive", "Descriptive"),
]

DATA_TYPE_CHOICES = [
    ("string", "Text"),
    ("integer", "Whole Number"),
    ("decimal", "Decimal Number"),
    ("date", "Date"),
]

CODE_FIELD_CHOICES = [
    ("attendance_url", "Attendance scan link"),
    ("reg_id", "Registration ID"),
    ("event_name", "Event Name"),
    ("participant_name", "Participant Name"),
    ("mobile", "Mobile Number"),
    ("email", "Email"),
    ("designation", "Designation"),
    ("subject", "Subject"),
    ("school_name", "School / Organization"),
    ("school_area", "Area / Place"),
    ("block", "Block"),
]

SYSTEM_FIELD_CHOICES = [
    ("salutation", "Salutation"),
    ("teacher_name", "Name Field"),
    ("mobile", "Mobile Number"),
    ("email", "Email Address"),
    ("designation", "Designation"),
    ("subject", "Subject"),
    ("school_name", "School / Organization Name"),
    ("school_area", "Area / Place"),
    ("block", "Block"),
]

PROTECTED_FIELD_NAMES = {"teacher_name", "mobile"}
SPONSOR_UPLOAD_FOLDER = os.path.join("static", "sponsors")
ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "webp", "gif"}

os.makedirs(SPONSOR_UPLOAD_FOLDER, exist_ok=True)


def checkbox_value(name):
    return name in request.form


def bounded_int(name, default, minimum, maximum):
    value = request.form.get(name, default, type=int)
    if value is None:
        value = default
    return min(max(value, minimum), maximum)


def choice_value(name, default, allowed):
    value = (request.form.get(name, default) or default).strip().lower()
    return value if value in allowed else default


def event_date_value():
    value = request.form.get("event_date", "").strip()
    try:
        return datetime.strptime(value, "%Y-%m-%d").date() if value else None
    except ValueError:
        return None


def save_sponsor_upload(field_name, existing_filename=""):
    upload = request.files.get(field_name)
    if not upload or not upload.filename:
        return existing_filename or ""

    original = secure_filename(upload.filename)
    ext = original.rsplit(".", 1)[-1].lower() if "." in original else ""
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        return existing_filename or ""

    filename = f"{field_name}_{uuid.uuid4().hex[:12]}.{ext}"
    upload.save(os.path.join(SPONSOR_UPLOAD_FOLDER, filename))
    return filename


def normalize_field_name(value):
    cleaned = re.sub(r"[^a-z0-9_]+", "_", (value or "").strip().lower())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    if not cleaned:
        cleaned = "custom_field"
    if cleaned[0].isdigit():
        cleaned = f"field_{cleaned}"
    return cleaned


def default_fields_for_type(registration_type):
    if registration_type == "no_registration":
        return []

    if registration_type == "student":
        return [
            {"field_name": "teacher_name", "field_label": "Student Name", "field_type": "text", "data_type": "string", "placeholder": "Enter student name", "is_required": True, "sort_order": 10},
            {"field_name": "mobile", "field_label": "Mobile Number", "field_type": "tel", "data_type": "string", "placeholder": "9876543210", "is_required": True, "sort_order": 20},
            {"field_name": "email", "field_label": "Email Address", "field_type": "email", "data_type": "string", "placeholder": "example@gmail.com", "is_required": False, "sort_order": 30},
            {"field_name": "school_name", "field_label": "School / College Name", "field_type": "text", "data_type": "string", "placeholder": "Enter school or college name", "is_required": True, "sort_order": 40},
        ]

    if registration_type == "public":
        return [
            {"field_name": "teacher_name", "field_label": "Participant Name", "field_type": "text", "data_type": "string", "placeholder": "Enter participant name", "is_required": True, "sort_order": 10},
            {"field_name": "mobile", "field_label": "Mobile Number", "field_type": "tel", "data_type": "string", "placeholder": "9876543210", "is_required": True, "sort_order": 20},
            {"field_name": "email", "field_label": "Email Address", "field_type": "email", "data_type": "string", "placeholder": "example@gmail.com", "is_required": False, "sort_order": 30},
        ]

    return [
        {"field_name": "salutation", "field_label": "Salutation", "field_type": "select", "data_type": "string", "options_text": "Mr.\nMrs.\nMs.\nDr.", "is_required": True, "sort_order": 10},
        {"field_name": "teacher_name", "field_label": "Teacher Name", "field_type": "text", "data_type": "string", "placeholder": "Enter teacher name", "is_required": True, "sort_order": 20},
        {"field_name": "mobile", "field_label": "Mobile Number", "field_type": "tel", "data_type": "string", "placeholder": "9876543210", "is_required": True, "sort_order": 30},
        {"field_name": "email", "field_label": "Email Address", "field_type": "email", "data_type": "string", "placeholder": "example@gmail.com", "is_required": True, "sort_order": 40},
    ]


def seed_event_fields(event):
    if event.registration_fields:
        return

    for item in default_fields_for_type(event.registration_type):
        db.session.add(
            EventField(
                event_id=event.id,
                field_name=item["field_name"],
                field_label=item["field_label"],
                field_type=item.get("field_type", "text"),
                data_type=item.get("data_type", "string"),
                placeholder=item.get("placeholder", ""),
                options_text=item.get("options_text", ""),
                is_required=bool(item.get("is_required", False)),
                is_active=True,
                sort_order=item.get("sort_order", 0),
            )
        )


def event_payload_from_form(event=None):
    collect_photo = checkbox_value("collect_photo")
    registration_type = request.form.get("registration_type", "teacher").strip() or "teacher"
    if registration_type == "no_registration":
        collect_photo = False

    payment_enabled = checkbox_value("payment_enabled")
    payment_amount_raw = request.form.get("payment_amount", "").strip()

    try:
        payment_amount = float(payment_amount_raw) if payment_amount_raw else 0
    except ValueError:
        payment_amount = 0

    code_type = request.form.get("code_type", "qr").strip().lower()
    if code_type not in {"qr", "barcode"}:
        code_type = "qr"

    code_fields = request.form.getlist("code_fields")
    if not code_fields:
        code_fields = ["attendance_url", "reg_id", "participant_name", "event_name"]

    reg_id_prefix = normalize_field_name(
        request.form.get("reg_id_prefix", "").strip() or "EVT"
    ).replace("_", "").upper()[:20]
    reg_id_next_number = request.form.get("reg_id_next_number", 1, type=int) or 1
    reg_id_padding = request.form.get("reg_id_padding", 4, type=int) or 4
    reg_id_next_number = max(1, reg_id_next_number)
    reg_id_padding = min(max(1, reg_id_padding), 10)

    return {
        "name": request.form.get("name", "").strip(),
        "slug": request.form.get("slug", "").strip(),
        "description": request.form.get("description", "").strip(),
        "registration_type": registration_type,
        "public_registration_enabled": checkbox_value("public_registration_enabled"),
        "participant_bulk_upload_enabled": checkbox_value("participant_bulk_upload_enabled"),
        "show_venue": checkbox_value("show_venue"),
        "venue": request.form.get("venue", "").strip(),
        "show_event_date": checkbox_value("show_event_date"),
        "event_date": event_date_value(),
        "show_event_time": checkbox_value("show_event_time"),
        "event_time": request.form.get("event_time", "").strip(),
        "show_chief_guest": checkbox_value("show_chief_guest"),
        "chief_guest": request.form.get("chief_guest", "").strip(),
        "collect_photo": collect_photo,
        "requires_photo": collect_photo and checkbox_value("requires_photo"),
        "collect_email": True,
        "collect_designation": True,
        "collect_subject": True,
        "collect_school_name": True,
        "collect_school_area": True,
        "collect_block": True,
        "marquee_message": request.form.get("marquee_message", "").strip(),
        "hero_priority": max(request.form.get("hero_priority", 0, type=int) or 0, 0),
        "payment_enabled": payment_enabled,
        "payment_amount": payment_amount,
        "payment_link": request.form.get("payment_link", "").strip(),
        "payment_notes": request.form.get("payment_notes", "").strip(),
        "whatsapp_ack_enabled": checkbox_value("whatsapp_ack_enabled"),
        "whatsapp_template": request.form.get("whatsapp_template", "").strip(),
        "whatsapp_group_enabled": checkbox_value("whatsapp_group_enabled"),
        "whatsapp_group_link": request.form.get("whatsapp_group_link", "").strip(),
        "acknowledgement_enabled": checkbox_value("acknowledgement_enabled"),
        "certificate_enabled": checkbox_value("certificate_enabled"),
        "attendance_enabled": checkbox_value("attendance_enabled"),
        "code_type": code_type,
        "code_fields": "\n".join(code_fields),
        "reg_id_prefix": reg_id_prefix,
        "reg_id_next_number": reg_id_next_number,
        "reg_id_padding": reg_id_padding,
        "sponsor_brand": request.form.get("sponsor_brand", "").strip(),
        "sponsor_logo": save_sponsor_upload(
            "sponsor_logo",
            event.sponsor_logo if event else ""
        ),
        "sponsor_image": save_sponsor_upload(
            "sponsor_image",
            event.sponsor_image if event else ""
        ),
        "sponsor_logo_position": choice_value(
            "sponsor_logo_position",
            "left",
            {"left", "center", "right"}
        ),
        "sponsor_logo_width": bounded_int("sponsor_logo_width", 160, 40, 400),
        "sponsor_logo_height": bounded_int("sponsor_logo_height", 90, 30, 240),
        "sponsor_banner_position": choice_value(
            "sponsor_banner_position",
            "right",
            {"left", "center", "right", "full"}
        ),
        "sponsor_banner_width": bounded_int("sponsor_banner_width", 520, 120, 1100),
        "sponsor_banner_height": bounded_int("sponsor_banner_height", 170, 60, 420),
        "sponsor_image_fit": choice_value(
            "sponsor_image_fit",
            "contain",
            {"contain", "cover", "fill"}
        ),
        "qr_sharing_enabled": checkbox_value("qr_sharing_enabled"),
        "exam_enabled": checkbox_value("exam_enabled"),
        "is_active": checkbox_value("is_active"),
    }


def event_field_payload_from_form():
    field_name = request.form.get("field_name", "").strip()
    custom_key = request.form.get("custom_field_name", "").strip()

    if field_name == "__custom__":
        field_name = custom_key

    normalized_name = normalize_field_name(field_name)

    return {
        "field_name": normalized_name,
        "field_label": request.form.get("field_label", "").strip(),
        "field_type": request.form.get("field_type", "text").strip() or "text",
        "data_type": request.form.get("data_type", "string").strip() or "string",
        "placeholder": request.form.get("placeholder", "").strip(),
        "options_text": request.form.get("options_text", "").strip(),
        "help_text": request.form.get("help_text", "").strip(),
        "is_required": checkbox_value("is_required"),
        "is_active": checkbox_value("is_active"),
        "sort_order": request.form.get("sort_order", 0, type=int),
    }


def exam_subject_payload_from_form():
    return {
        "subject_name": request.form.get("subject_name", "").strip(),
        "description": request.form.get("description", "").strip(),
        "is_active": checkbox_value("is_active"),
    }


def online_exam_payload_from_form():
    exam_code = normalize_field_name(
        request.form.get("exam_code", "").strip()
    ).replace("_", "-")

    return {
        "subject_id": request.form.get("subject_id", type=int),
        "exam_title": request.form.get("exam_title", "").strip(),
        "exam_code": exam_code,
        "instructions": request.form.get("instructions", "").strip(),
        "start_at": parse_datetime_value(request.form.get("start_at", "").strip()),
        "end_at": parse_datetime_value(request.form.get("end_at", "").strip()),
        "duration_minutes": request.form.get("duration_minutes", 30, type=int) or 30,
        "marks_per_question": request.form.get("marks_per_question", 1, type=float) or 1,
        "pass_mark": request.form.get("pass_mark", 0, type=float) or 0,
        "negative_marks": request.form.get("negative_marks", 0, type=float) or 0,
        "max_attempts": request.form.get("max_attempts", 1, type=int) or 1,
        "tab_switch_limit": request.form.get("tab_switch_limit", 3, type=int) or 3,
        "auto_submit_on_violation": checkbox_value("auto_submit_on_violation"),
        "show_result_immediately": checkbox_value("show_result_immediately"),
        "public_results_published": checkbox_value("public_results_published"),
        "is_active": checkbox_value("is_active"),
    }


def exam_question_payload_from_form():
    return {
        "question_type": request.form.get("question_type", "mcq").strip() or "mcq",
        "question_text": request.form.get("question_text", "").strip(),
        "option_a": request.form.get("option_a", "").strip(),
        "option_b": request.form.get("option_b", "").strip(),
        "option_c": request.form.get("option_c", "").strip(),
        "option_d": request.form.get("option_d", "").strip(),
        "correct_option": request.form.get("correct_option", "A").strip() or "A",
        "model_answer": request.form.get("model_answer", "").strip(),
        "explanation": request.form.get("explanation", "").strip(),
        "marks": request.form.get("marks", 1, type=float) or 1,
        "sort_order": request.form.get("sort_order", 0, type=int),
        "is_active": checkbox_value("is_active"),
    }


def parse_datetime_value(value):
    if not value:
        return None

    for fmt in ("%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def recalculate_attempt_scores(attempt):
    total_marks = 0.0
    score = 0.0
    correct_answers = 0
    pending = False

    for answer in attempt.answers:
        question_marks = float((answer.question.marks if answer.question else 0) or 0)
        total_marks += question_marks
        awarded = answer.awarded_score
        score += awarded

        if answer.question and answer.question.question_type == "descriptive":
            if answer.manual_score is None:
                pending = True
        elif answer.is_correct:
            correct_answers += 1

    attempt.total_marks = total_marks
    attempt.score = score
    attempt.correct_answers = correct_answers
    attempt.total_questions = len(attempt.answers)
    attempt.evaluation_status = "pending_review" if pending else "evaluated"


def online_exam_status(exam):
    now = datetime.utcnow()
    if exam.start_at and now < exam.start_at:
        return "Upcoming"
    if exam.end_at and now > exam.end_at:
        return "Closed"
    if exam.is_active:
        return "Open"
    return "Draft"


def build_exam_dashboard(selected_event_id=None, selected_exam_id=None):
    event_query = Event.query
    exam_query = OnlineExam.query
    subject_query = ExamSubject.query
    participant_query = Participant.query

    if selected_event_id:
        event_query = event_query.filter(Event.id == selected_event_id)
        exam_query = exam_query.filter(OnlineExam.event_id == selected_event_id)
        subject_query = subject_query.filter(ExamSubject.event_id == selected_event_id)
        participant_query = participant_query.filter(Participant.event_id == selected_event_id)

    if selected_exam_id:
        exam_query = exam_query.filter(OnlineExam.id == selected_exam_id)

    events = event_query.all()
    exams = exam_query.all()
    subjects = subject_query.all()
    exam_ids = [exam.id for exam in exams]

    attempt_query = ExamAttempt.query
    if selected_exam_id:
        attempt_query = attempt_query.filter(ExamAttempt.exam_id == selected_exam_id)
    elif exam_ids:
        attempt_query = attempt_query.filter(ExamAttempt.exam_id.in_(exam_ids))
    else:
        attempt_query = attempt_query.filter(False)

    attempts = attempt_query.order_by(ExamAttempt.submitted_at.desc()).all()
    event_ids = [event.id for event in events]
    exam_users = participant_query.filter(Participant.exam_username.isnot(None)).count()

    active_exams = len([exam for exam in exams if exam.is_active])
    total_questions = sum(len(exam.questions) for exam in exams)
    passed = len([
        attempt for attempt in attempts
        if attempt.exam and attempt.score >= (attempt.exam.pass_mark or 0)
    ])
    failed = len([
        attempt for attempt in attempts
        if attempt.exam and attempt.score < (attempt.exam.pass_mark or 0)
    ])
    pending_review = len([
        attempt for attempt in attempts
        if attempt.evaluation_status == "pending_review"
    ])
    violations = sum(int(attempt.violation_count or 0) for attempt in attempts)
    avg_score = round(
        sum(float(attempt.score or 0) for attempt in attempts) / len(attempts),
        2
    ) if attempts else 0

    by_event = {}
    for event in events:
        event_exam_ids = [exam.id for exam in event.online_exams]
        by_event[event.name] = len([
            attempt for attempt in attempts
            if attempt.exam_id in event_exam_ids
        ])

    by_subject = {}
    for attempt in attempts:
        subject_name = (
            attempt.exam.subject.subject_name
            if attempt.exam and attempt.exam.subject
            else "Not Set"
        )
        by_subject[subject_name] = by_subject.get(subject_name, 0) + 1

    status_counts = {}
    for exam in exams:
        status = online_exam_status(exam)
        status_counts[status] = status_counts.get(status, 0) + 1

    return {
        "stats": {
            "events": len(events),
            "exam_enabled_events": len([event for event in events if event.exam_enabled]),
            "subjects": len(subjects),
            "exams": len(exams),
            "active_exams": active_exams,
            "questions": total_questions,
            "exam_users": exam_users,
            "attempts": len(attempts),
            "passed": passed,
            "failed": failed,
            "avg_score": avg_score,
            "violations": violations,
            "pending_review": pending_review,
        },
        "charts": {
            "by_event": by_event,
            "by_subject": by_subject,
            "status_counts": status_counts,
            "result_counts": {
                "Passed": passed,
                "Failed": failed,
                "Pending Review": pending_review,
            },
        },
        "recent_attempts": attempts[:12],
    }


def extract_registration_id_from_scan(scan_text, event_id=None):
    value = (scan_text or "").strip()
    if not value:
        return ""

    patterns = [
        r"Registration\s*Id\s*:\s*([A-Za-z0-9\-]+)",
        r"Registration\s*ID\s*:\s*([A-Za-z0-9\-]+)",
        r"/attendance/mark/([A-Za-z0-9\-]+)",
        r"reg_id=([A-Za-z0-9\-]+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, value, re.IGNORECASE)
        if match:
            return match.group(1).upper()

    compact = value.strip().splitlines()[0].strip().upper()
    if re.fullmatch(r"[A-Z0-9\-]+", compact):
        return compact

    query = Participant.query
    if event_id:
        query = query.filter(Participant.event_id == event_id)

    for participant in query.order_by(Participant.created_at.desc()).limit(500).all():
        if participant.reg_id and participant.reg_id.upper() in value.upper():
            return participant.reg_id

    return ""


def mark_participant_present(participant):
    if not participant or not participant.event or not participant.event.attendance_enabled:
        return False

    result = service_mark_attendance(
        participant,
        "QR",
        str(session.get("admin") or "Admin"),
        request.remote_addr or ""
    )
    return bool(result.get("ok"))


# =====================================================
# ADMIN DASHBOARD
# =====================================================
@admin_bp.route("/admin")
def admin():

    if "admin" not in session:
        return redirect(url_for("routes.login"))

    search = request.args.get("search", "")
    page = request.args.get("page", 1, type=int)
    selected_event_id = request.args.get("event_id", type=int)

    query = Participant.query

    if selected_event_id:
        query = query.filter(
            Participant.event_id == selected_event_id
        )

    if search:
        query = query.filter(
            (Participant.teacher_name.contains(search)) |
            (Participant.mobile.contains(search)) |
            (Participant.reg_id.contains(search)) |
            (Participant.exam_username.contains(search))
        )

    participants = query.order_by(
        Participant.id.desc()
    ).paginate(
        page=page,
        per_page=20,
        error_out=False
    )

    total = Participant.query.count()
    events = Event.query.order_by(
        Event.hero_priority.desc(),
        Event.is_active.desc(),
        Event.created_at.desc(),
        Event.id.desc()
    ).all()

    for participant in participants.items:
        participant.extra_items = participant.extra_data_items()

    return render_template(
        "admin/dashboard.html",
        participants=participants,
        search=search,
        total=total,
        events=events,
        selected_event_id=selected_event_id
    )


COMPETITION_RANK_OPTIONS = ["Winner", "Runner", "1st Place", "2nd Place", "3rd Place", "Participant Certificate"]


def competition_admin_redirect(competition_id=None, **params):
    endpoint = "admin.competition_results_admin" if competition_id else "admin.competitions"
    if competition_id:
        return redirect(url_for(endpoint, competition_id=competition_id, **params))
    return redirect(url_for(endpoint, **params))


@admin_bp.route("/admin/competitions", methods=["GET", "POST"])
def competitions():
    if "admin" not in session:
        return redirect(url_for("routes.login"))
    events = Event.query.order_by(Event.created_at.desc(), Event.id.desc()).all()
    if request.method == "POST":
        event_id = request.form.get("event_id", type=int)
        name = request.form.get("name", "").strip()
        if not Event.query.get(event_id) or not name:
            return competition_admin_redirect(error="missing_fields")
        db.session.add(Competition(
            event_id=event_id,
            name=name,
            category=request.form.get("category", "").strip(),
            description=request.form.get("description", "").strip(),
            registration_enabled=bool(request.form.get("registration_enabled")),
        ))
        db.session.commit()
        return competition_admin_redirect(created=1)
    competition_rows = Competition.query.order_by(Competition.created_at.desc(), Competition.id.desc()).all()
    stats = []
    for competition in competition_rows:
        registrations = competition.registrations
        stats.append({
            "competition": competition,
            "total": len(registrations),
            "male": sum(row.gender.lower() == "male" for row in registrations),
            "female": sum(row.gender.lower() == "female" for row in registrations),
            "winners": [row for row in registrations if row.rank in COMPETITION_RANK_OPTIONS[:5]],
        })
    return render_template("admin/competitions.html", events=events, stats=stats)


@admin_bp.route("/admin/competitions/<int:competition_id>/settings", methods=["POST"])
def update_competition_settings(competition_id):
    if "admin" not in session:
        return redirect(url_for("routes.login"))
    competition = Competition.query.get_or_404(competition_id)
    competition.registration_enabled = bool(request.form.get("registration_enabled"))
    competition.results_published = bool(request.form.get("results_published"))
    db.session.commit()
    return competition_admin_redirect(updated=1)


@admin_bp.route("/admin/competitions/<int:competition_id>/judges", methods=["POST"])
def add_competition_judge(competition_id):
    if "admin" not in session:
        return redirect(url_for("routes.login"))
    competition = Competition.query.get_or_404(competition_id)
    name = request.form.get("name", "").strip()
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    if not name or not username or not password or CompetitionJudge.query.filter_by(username=username).first():
        return competition_admin_redirect(competition.id, judge_error=1)
    db.session.add(CompetitionJudge(
        competition_id=competition.id,
        name=name,
        username=username,
        password_hash=generate_password_hash(password),
    ))
    db.session.commit()
    return competition_admin_redirect(competition.id, judge_created=1)


@admin_bp.route("/admin/competitions/<int:competition_id>/results", methods=["GET", "POST"])
def competition_results_admin(competition_id):
    if "admin" not in session:
        return redirect(url_for("routes.login"))
    competition = Competition.query.get_or_404(competition_id)
    registrations = CompetitionRegistration.query.filter_by(competition_id=competition.id).order_by(CompetitionRegistration.participant_name).all()
    if request.method == "POST":
        try:
            for registration in registrations:
                score = float(request.form.get(f"score_{registration.id}", ""))
                rank = request.form.get(f"rank_{registration.id}", "Participant Certificate")
                if not math.isfinite(score) or score < 0 or rank not in COMPETITION_RANK_OPTIONS:
                    raise ValueError
                registration.score = score
                registration.rank = rank
                registration.is_present = request.form.get(f"attendance_{registration.id}") == "present"
            db.session.commit()
            return competition_admin_redirect(competition.id, saved=1)
        except ValueError:
            return competition_admin_redirect(competition.id, score_error=1)
    return render_template(
        "admin/competition_results.html", competition=competition, registrations=registrations,
        ranks=COMPETITION_RANK_OPTIONS,
    )


@admin_bp.route("/admin/attendance", methods=["GET", "POST"])
def attendance():

    if "admin" not in session:
        return redirect(url_for("routes.login"))

    selected_event_id = request.values.get("event_id", type=int)
    scan_text = request.form.get("scan_text", "")
    message = request.args.get("message", "")
    message_type = request.args.get("message_type", "info")

    if request.method == "POST":
        reg_id = extract_registration_id_from_scan(scan_text, selected_event_id)
        participant = Participant.query.filter_by(reg_id=reg_id).first() if reg_id else None

        if participant and selected_event_id and participant.event_id != selected_event_id:
            participant = None

        if mark_participant_present(participant):
            message = f"{participant.teacher_name} ({participant.reg_id}) marked present."
            message_type = "success"
        else:
            message = "No matching participant found, or attendance is not enabled for this event."
            message_type = "danger"

    events = Event.query.order_by(Event.created_at.desc(), Event.id.desc()).all()
    query = Participant.query.join(Event).filter(Event.attendance_enabled == True)

    if selected_event_id:
        query = query.filter(Participant.event_id == selected_event_id)

    participants = query.order_by(
        Participant.is_present.desc(),
        Participant.attendance_marked_at.desc(),
        Participant.created_at.desc()
    ).limit(200).all()

    total_count = len(participants)
    present_count = len([item for item in participants if item.is_present])

    return render_template(
        "admin/attendance.html",
        events=events,
        participants=participants,
        selected_event_id=selected_event_id,
        total_count=total_count,
        present_count=present_count,
        message=message,
        message_type=message_type
    )


@admin_bp.route("/admin/attendance/mark/<reg_id>")
def mark_attendance(reg_id):

    if "admin" not in session:
        return redirect(url_for("routes.login"))

    participant = Participant.query.filter_by(reg_id=reg_id.upper()).first()

    if mark_participant_present(participant):
        return redirect(url_for(
            "attendance.dashboard",
            event_id=participant.event_id,
            message=f"{participant.teacher_name} ({participant.reg_id}) marked present.",
            message_type="success"
        ))

    return redirect(url_for(
        "attendance.dashboard",
        message="Attendance is not enabled or participant was not found.",
        message_type="danger"
    ))


@admin_bp.route("/admin/participants/<int:id>/exam-credentials", methods=["POST"])
def update_exam_credentials(id):

    if "admin" not in session:
        return redirect(url_for("routes.login"))

    participant = Participant.query.get_or_404(id)
    username = request.form.get("exam_username", "").strip()
    password = request.form.get("exam_password", "")

    if username:
        existing = Participant.query.filter(
            Participant.exam_username == username,
            Participant.id != participant.id
        ).first()

        if existing:
            return redirect(request.referrer or url_for("admin.admin"))

        participant.exam_username = username

    if password:
        participant.exam_password_hash = generate_password_hash(password)

    if not username:
        participant.exam_username = None
        participant.exam_password_hash = None

    db.session.commit()

    return redirect(request.referrer or url_for("admin.admin"))


def unique_exam_reg_id():
    while True:
        reg_id = f"EXAM{uuid.uuid4().hex[:10].upper()}"
        if not Participant.query.filter_by(reg_id=reg_id).first():
            return reg_id


def row_value(row, *names):
    for name in names:
        value = row.get(name)
        if pd.notna(value):
            if isinstance(value, float) and value.is_integer():
                value = int(value)
            value = str(value).strip()
            if value:
                return value
    return ""


def duty_redirect(event_id, **params):
    return redirect(url_for("admin.exam_duty_allocation", event_id=event_id, **params))


@admin_bp.route("/admin/exam-duty-allocation")
def exam_duty_allocation():
    if "admin" not in session:
        return redirect(url_for("routes.login"))

    events = Event.query.order_by(Event.created_at.desc(), Event.id.desc()).all()
    event_id = request.args.get("event_id", type=int)
    event = Event.query.get(event_id) if event_id else (events[0] if events else None)
    teachers = []
    centers = []
    allocations = []
    if event:
        teachers = ExamDutyTeacher.query.filter_by(event_id=event.id).order_by(ExamDutyTeacher.teacher_name).all()
        centers = ExamDutyCenter.query.filter_by(event_id=event.id).order_by(ExamDutyCenter.center_no).all()
        allocations = ExamDutyAllocation.query.filter_by(event_id=event.id).join(ExamDutyCenter).order_by(ExamDutyCenter.center_no, ExamDutyAllocation.id).all()

    allocated_count = len(allocations)
    required_count = sum(center.invigilators_required for center in centers)
    return render_template(
        "admin/exam_duty_allocation.html", events=events, event=event,
        teachers=teachers, centers=centers, allocations=allocations,
        allocated_count=allocated_count, required_count=required_count,
    )


@admin_bp.route("/admin/exam-duty-allocation/<int:event_id>/teachers/import", methods=["POST"])
def import_exam_duty_teachers(event_id):
    if "admin" not in session:
        return redirect(url_for("routes.login"))
    event = Event.query.get_or_404(event_id)
    upload = request.files.get("teachers_file")
    if not upload or not upload.filename:
        return duty_redirect(event.id, teacher_import_error="missing_file")
    try:
        frame = pd.read_csv(upload) if upload.filename.lower().endswith(".csv") else pd.read_excel(upload)
    except Exception:
        return duty_redirect(event.id, teacher_import_error="invalid_file")

    frame.columns = [str(column).strip().lower().replace(" ", "_") for column in frame.columns]
    created = updated = skipped = 0
    for _, row in frame.iterrows():
        teacher_id = row_value(row, "teacher_id", "teacherid", "staff_id", "employee_id")
        name = row_value(row, "teacher_name", "name", "staff_name")
        udise_code = row_value(row, "udise_code", "udise", "school_udise_code")
        working_school = row_value(row, "working_school", "school_name", "school")
        working_block = row_value(row, "working_block", "block", "school_block")
        if not teacher_id or not name or not udise_code or not working_block:
            skipped += 1
            continue
        teacher = ExamDutyTeacher.query.filter_by(event_id=event.id, teacher_id=teacher_id).first()
        values = {
            "teacher_name": name, "mobile": row_value(row, "mobile", "mobile_number", "phone"),
            "designation": row_value(row, "designation"), "working_school": working_school,
            "udise_code": udise_code, "working_block": working_block, "is_active": True,
        }
        if teacher:
            for key, value in values.items():
                setattr(teacher, key, value)
            updated += 1
        else:
            db.session.add(ExamDutyTeacher(event_id=event.id, teacher_id=teacher_id, **values))
            created += 1
    db.session.commit()
    return duty_redirect(event.id, teacher_import_created=created, teacher_import_updated=updated, teacher_import_skipped=skipped)


@admin_bp.route("/admin/exam-duty-allocation/<int:event_id>/centers", methods=["POST"])
def add_exam_duty_center(event_id):
    if "admin" not in session:
        return redirect(url_for("routes.login"))
    event = Event.query.get_or_404(event_id)
    center_name = request.form.get("center_name", "").strip()
    center_no = request.form.get("center_no", "").strip()
    center_block = request.form.get("center_block", "").strip()
    required = max(request.form.get("invigilators_required", 1, type=int) or 1, 1)
    if not center_name or not center_no or not center_block:
        return duty_redirect(event.id, center_error="missing_fields")
    existing = ExamDutyCenter.query.filter_by(event_id=event.id, center_no=center_no).first()
    if existing:
        existing.center_name, existing.center_block, existing.invigilators_required = center_name, center_block, required
    else:
        db.session.add(ExamDutyCenter(event_id=event.id, center_name=center_name, center_no=center_no, center_block=center_block, invigilators_required=required))
    db.session.commit()
    return duty_redirect(event.id)


@admin_bp.route("/admin/exam-duty-allocation/<int:event_id>/centers/import", methods=["POST"])
def import_exam_duty_centers(event_id):
    if "admin" not in session:
        return redirect(url_for("routes.login"))
    event = Event.query.get_or_404(event_id)
    upload = request.files.get("centers_file")
    if not upload or not upload.filename:
        return duty_redirect(event.id, center_import_error="missing_file")
    try:
        frame = pd.read_csv(upload) if upload.filename.lower().endswith(".csv") else pd.read_excel(upload)
    except Exception:
        return duty_redirect(event.id, center_import_error="invalid_file")

    frame.columns = [str(column).strip().lower().replace(" ", "_") for column in frame.columns]
    created = updated = skipped = 0
    for _, row in frame.iterrows():
        center_name = row_value(row, "center_name", "exam_center_name", "name")
        center_no = row_value(row, "center_no", "center_number", "exam_center_no", "exam_center_number")
        center_block = row_value(row, "center_block", "exam_center_block", "block")
        required_value = row_value(row, "invigilators_required", "required_invigilators", "invigilator_count", "no_of_invigilators")
        try:
            required = max(int(float(required_value)), 1)
        except (TypeError, ValueError):
            required = 0
        if not center_name or not center_no or not center_block or not required:
            skipped += 1
            continue
        center = ExamDutyCenter.query.filter_by(event_id=event.id, center_no=center_no).first()
        if center:
            center.center_name = center_name
            center.center_block = center_block
            center.invigilators_required = required
            updated += 1
        else:
            db.session.add(ExamDutyCenter(
                event_id=event.id,
                center_name=center_name,
                center_no=center_no,
                center_block=center_block,
                invigilators_required=required,
            ))
            created += 1
    db.session.commit()
    return duty_redirect(event.id, center_import_created=created, center_import_updated=updated, center_import_skipped=skipped)


def duty_candidates(event, center):
    allocated_teacher_ids = {
        allocation.teacher_id for allocation in ExamDutyAllocation.query.filter_by(event_id=event.id).all()
    }
    teachers = ExamDutyTeacher.query.filter_by(event_id=event.id, is_active=True).filter(~ExamDutyTeacher.id.in_(allocated_teacher_ids or [-1])).all()
    # Teachers from a different working block are selected first to avoid local-school assignments.
    external = [teacher for teacher in teachers if teacher.working_block.strip().lower() != center.center_block.strip().lower()]
    local = [teacher for teacher in teachers if teacher not in external]
    random.shuffle(external)
    random.shuffle(local)
    return external + local


def lottery_candidates(event):
    allocated_teacher_ids = {
        allocation.teacher_id for allocation in ExamDutyAllocation.query.filter_by(event_id=event.id).all()
    }
    teachers = ExamDutyTeacher.query.filter_by(event_id=event.id, is_active=True).filter(
        ~ExamDutyTeacher.id.in_(allocated_teacher_ids or [-1])
    ).all()
    random.shuffle(teachers)
    return teachers


@admin_bp.route("/admin/exam-duty-allocation/<int:event_id>/allocate-lot", methods=["POST"])
def allocate_exam_duty_lot(event_id):
    if "admin" not in session:
        return redirect(url_for("routes.login"))
    event = Event.query.get_or_404(event_id)
    center = ExamDutyCenter.query.filter_by(id=request.form.get("center_id", type=int), event_id=event.id).first()
    if not center:
        return duty_redirect(event.id, allocation_error="invalid_center")
    current = ExamDutyAllocation.query.filter_by(event_id=event.id, center_id=center.id).count()
    count = min(max(request.form.get("count", 1, type=int) or 1, 1), max(center.invigilators_required - current, 0))
    # A lottery is a random draw from all eligible, unallocated teachers.
    selected = lottery_candidates(event)[:count]
    for teacher in selected:
        db.session.add(ExamDutyAllocation(event_id=event.id, teacher_id=teacher.id, center_id=center.id, allocation_method="lot"))
    db.session.commit()
    return duty_redirect(event.id, lot_allocated=len(selected))


@admin_bp.route("/admin/exam-duty-allocation/<int:event_id>/allocate-auto", methods=["POST"])
def allocate_exam_duty_auto(event_id):
    if "admin" not in session:
        return redirect(url_for("routes.login"))
    event = Event.query.get_or_404(event_id)
    if request.form.get("replace_existing"):
        ExamDutyAllocation.query.filter_by(event_id=event.id).delete()
        db.session.flush()
    allocated = 0
    centers = ExamDutyCenter.query.filter_by(event_id=event.id).order_by(ExamDutyCenter.center_no).all()
    for center in centers:
        current = ExamDutyAllocation.query.filter_by(event_id=event.id, center_id=center.id).count()
        slots = max(center.invigilators_required - current, 0)
        for teacher in duty_candidates(event, center)[:slots]:
            db.session.add(ExamDutyAllocation(event_id=event.id, teacher_id=teacher.id, center_id=center.id, allocation_method="auto"))
            db.session.flush()
            allocated += 1
    db.session.commit()
    return duty_redirect(event.id, auto_allocated=allocated)


@admin_bp.route("/admin/exam-duty-allocation/<int:event_id>/allocate-manual", methods=["POST"])
def allocate_exam_duty_manual(event_id):
    if "admin" not in session:
        return redirect(url_for("routes.login"))
    event = Event.query.get_or_404(event_id)
    teacher = ExamDutyTeacher.query.filter_by(id=request.form.get("teacher_id", type=int), event_id=event.id).first()
    center = ExamDutyCenter.query.filter_by(id=request.form.get("center_id", type=int), event_id=event.id).first()
    if not teacher or not center or ExamDutyAllocation.query.filter_by(event_id=event.id, teacher_id=teacher.id).first():
        return duty_redirect(event.id, allocation_error="invalid_teacher")
    if ExamDutyAllocation.query.filter_by(event_id=event.id, center_id=center.id).count() >= center.invigilators_required:
        return duty_redirect(event.id, allocation_error="center_full")
    db.session.add(ExamDutyAllocation(event_id=event.id, teacher_id=teacher.id, center_id=center.id, allocation_method="manual"))
    db.session.commit()
    return duty_redirect(event.id)


@admin_bp.route("/admin/events/<int:event_id>/participants/import", methods=["POST"])
def import_event_participants(event_id):
    if "admin" not in session:
        return redirect(url_for("routes.login"))

    event = Event.query.get_or_404(event_id)
    upload = request.files.get("participants_file")
    if not event.participant_bulk_upload_enabled or not upload or not upload.filename:
        return redirect(url_for("admin.edit_event", id=event.id, participant_import_error="missing_file"))

    try:
        frame = pd.read_csv(upload) if upload.filename.lower().endswith(".csv") else pd.read_excel(upload)
    except Exception:
        return redirect(url_for("admin.edit_event", id=event.id, participant_import_error="invalid_file"))

    frame.columns = [str(column).strip().lower().replace(" ", "_") for column in frame.columns]
    created = updated = skipped = 0
    for _, row in frame.iterrows():
        name = row_value(row, "name", "participant_name", "teacher_name", "student_name")
        mobile = row_value(row, "mobile", "mobile_number", "phone")
        if not name or not mobile:
            skipped += 1
            continue

        participant = Participant.query.filter_by(event_id=event.id, mobile=mobile).first()
        if not participant:
            participant = Participant(
                reg_id=registration_id_for_event(event), event_id=event.id,
                teacher_name=name, mobile=mobile,
                email=row_value(row, "email", "email_address") or f"{mobile}@participant.local",
                salutation=row_value(row, "salutation"),
                designation=row_value(row, "designation") or "Participant",
                subject=row_value(row, "subject") or "",
                school_name=row_value(row, "school_name", "school", "organization") or "",
                school_area=row_value(row, "school_area", "area", "place") or "",
                block=row_value(row, "block") or "",
                extra_data=json.dumps({
                    key: {"label": key.replace("_", " ").title(), "value": row_value(row, key)}
                    for key in frame.columns
                    if key not in {"name", "participant_name", "teacher_name", "student_name", "mobile", "mobile_number", "phone", "email", "email_address", "salutation", "designation", "subject", "school_name", "school", "organization", "school_area", "area", "place", "block"} and row_value(row, key)
                }),
            )
            db.session.add(participant)
            db.session.flush()
            created += 1
        else:
            participant.teacher_name = name
            participant.email = row_value(row, "email", "email_address") or participant.email
            participant.designation = row_value(row, "designation") or participant.designation
            updated += 1

        # Every imported participant receives the same code used by QR attendance.
        generate_participant_code(event, participant)

    db.session.commit()
    return redirect(url_for("admin.edit_event", id=event.id, participant_import_created=created, participant_import_updated=updated, participant_import_skipped=skipped))


@admin_bp.route("/admin/events/<int:event_id>/exam-users/import", methods=["POST"])
def import_exam_users(event_id):

    if "admin" not in session:
        return redirect(url_for("routes.login"))

    event = Event.query.get_or_404(event_id)
    upload = request.files.get("exam_users_file")

    if not upload or not upload.filename:
        return redirect(url_for("admin.manage_event_exams", event_id=event.id, import_error="missing_file"))

    filename = upload.filename.lower()

    try:
        if filename.endswith(".csv"):
            frame = pd.read_csv(upload)
        else:
            frame = pd.read_excel(upload)
    except Exception:
        return redirect(url_for("admin.manage_event_exams", event_id=event.id, import_error="invalid_file"))

    frame.columns = [
        str(column).strip().lower().replace(" ", "_")
        for column in frame.columns
    ]

    created = 0
    updated = 0
    skipped = 0

    for _, row in frame.iterrows():
        username = row_value(row, "username", "user_name", "exam_username", "login_username")
        password = row_value(row, "password", "exam_password", "login_password")
        name = row_value(row, "name", "participant_name", "teacher_name", "student_name")
        unique_id = row_value(
            row,
            "unique_id",
            "admin_number",
            "admin_id",
            "id_number",
            "roll_no",
            "roll_number",
            "mobile",
            "mobile_number",
            "phone"
        )

        if not username or not password or not name or not unique_id:
            skipped += 1
            continue

        participant = Participant.query.filter_by(
            exam_username=username
        ).first()

        if participant and participant.event_id != event.id:
            skipped += 1
            continue

        if not participant:
            participant = Participant.query.filter_by(
                event_id=event.id,
                mobile=unique_id
            ).first()

        if not participant:
            email = row_value(row, "email", "email_address") or f"{username}@exam.local"

            participant = Participant(
                reg_id=unique_exam_reg_id(),
                event_id=event.id,
                salutation="",
                teacher_name=name,
                mobile=unique_id,
                email=email,
                designation=row_value(row, "designation") or "Exam User",
                subject=row_value(row, "subject") or "Exam",
                school_name=row_value(row, "school_name", "school", "organization") or "Exam User",
                school_area=row_value(row, "school_area", "area", "place") or "Exam User",
                block=row_value(row, "block") or "Exam",
                photo="",
                extra_data=json.dumps({
                    "exam_unique_id": {
                        "label": "Exam Unique ID",
                        "value": unique_id
                    }
                }),
            )
            db.session.add(participant)
            created += 1
        else:
            updated += 1
            participant.teacher_name = name or participant.teacher_name

        participant.exam_username = username
        participant.exam_password_hash = generate_password_hash(password)

    db.session.commit()

    return redirect(url_for(
        "admin.manage_event_exams",
        event_id=event.id,
        import_created=created,
        import_updated=updated,
        import_skipped=skipped
    ))


@admin_bp.route("/admin/events", methods=["GET", "POST"])
def events():

    if "admin" not in session:
        return redirect(url_for("routes.login"))

    if request.method == "POST":
        payload = event_payload_from_form()
        name = payload["name"]
        slug = payload["slug"]

        if name and slug:
            exists = Event.query.filter_by(
                slug=slug
            ).first()

            if not exists:
                event = Event(**payload)
                db.session.add(event)
                db.session.commit()
                seed_event_fields(event)
                db.session.commit()

        return redirect(url_for("admin.events"))

    events = Event.query.order_by(
        Event.is_active.desc(),
        Event.created_at.desc(),
        Event.id.desc()
    ).all()

    return render_template(
        "admin/events.html",
        events=events,
        registration_type_choices=REGISTRATION_TYPE_CHOICES,
        code_field_choices=CODE_FIELD_CHOICES
    )


@admin_bp.route("/admin/events/<int:id>/edit", methods=["GET", "POST"])
def edit_event(id):

    if "admin" not in session:
        return redirect(url_for("routes.login"))

    event = Event.query.get_or_404(id)
    if not event.registration_fields:
        seed_event_fields(event)
        db.session.commit()

    if request.method == "POST":
        payload = event_payload_from_form(event)

        existing = Event.query.filter(
            Event.slug == payload["slug"],
            Event.id != event.id
        ).first()

        if not existing and payload["name"] and payload["slug"]:
            for key, value in payload.items():
                setattr(event, key, value)
            db.session.commit()
            return redirect(url_for("admin.events"))

    return render_template(
        "admin/event_edit.html",
        event=event,
        registration_type_choices=REGISTRATION_TYPE_CHOICES,
        field_type_choices=FIELD_TYPE_CHOICES,
        data_type_choices=DATA_TYPE_CHOICES,
        code_field_choices=CODE_FIELD_CHOICES,
        system_field_choices=SYSTEM_FIELD_CHOICES
    )


@admin_bp.route("/admin/exams")
def exams_dashboard():

    if "admin" not in session:
        return redirect(url_for("routes.login"))

    selected_event_id = request.args.get("event_id", type=int)
    selected_exam_id = request.args.get("exam_id", type=int)

    events = Event.query.order_by(
        Event.exam_enabled.desc(),
        Event.created_at.desc(),
        Event.id.desc()
    ).all()

    exam_options_query = OnlineExam.query.order_by(
        OnlineExam.created_at.desc(),
        OnlineExam.id.desc()
    )
    if selected_event_id:
        exam_options_query = exam_options_query.filter(
            OnlineExam.event_id == selected_event_id
        )

    exam_options = exam_options_query.all()
    dashboard = build_exam_dashboard(selected_event_id, selected_exam_id)

    return render_template(
        "admin/exams_dashboard.html",
        events=events,
        exam_options=exam_options,
        selected_event_id=selected_event_id,
        selected_exam_id=selected_exam_id,
        dashboard=dashboard,
        online_exam_status=online_exam_status,
    )


@admin_bp.route("/admin/events/<int:event_id>/exams", methods=["GET", "POST"])
def manage_event_exams(event_id):

    if "admin" not in session:
        return redirect(url_for("routes.login"))

    event = Event.query.get_or_404(event_id)

    if request.method == "POST":
        payload = online_exam_payload_from_form()
        subject = ExamSubject.query.filter_by(
            id=payload["subject_id"],
            event_id=event.id
        ).first()

        if subject and payload["exam_title"] and payload["exam_code"]:
            exists = OnlineExam.query.filter_by(
                exam_code=payload["exam_code"]
            ).first()

            if not exists:
                db.session.add(
                    OnlineExam(
                        event_id=event.id,
                        **payload
                    )
                )
                db.session.commit()

        return redirect(url_for("admin.manage_event_exams", event_id=event.id))

    return render_template(
        "admin/event_exams.html",
        event=event,
        subjects=ExamSubject.query.filter_by(event_id=event.id).order_by(ExamSubject.subject_name.asc()).all(),
        exams=OnlineExam.query.filter_by(event_id=event.id).order_by(OnlineExam.created_at.desc()).all()
    )


@admin_bp.route("/admin/events/<int:event_id>/subjects", methods=["POST"])
def add_exam_subject(event_id):

    if "admin" not in session:
        return redirect(url_for("routes.login"))

    event = Event.query.get_or_404(event_id)
    payload = exam_subject_payload_from_form()

    if payload["subject_name"]:
        exists = ExamSubject.query.filter_by(
            event_id=event.id,
            subject_name=payload["subject_name"]
        ).first()

        if not exists:
            db.session.add(ExamSubject(event_id=event.id, **payload))
            db.session.commit()

    return redirect(url_for("admin.manage_event_exams", event_id=event.id))


@admin_bp.route("/admin/subjects/<int:subject_id>/edit", methods=["GET", "POST"])
def edit_exam_subject(subject_id):

    if "admin" not in session:
        return redirect(url_for("routes.login"))

    subject = ExamSubject.query.get_or_404(subject_id)

    if request.method == "POST":
        payload = exam_subject_payload_from_form()
        existing = ExamSubject.query.filter(
            ExamSubject.event_id == subject.event_id,
            ExamSubject.subject_name == payload["subject_name"],
            ExamSubject.id != subject.id
        ).first()

        if payload["subject_name"] and not existing:
            for key, value in payload.items():
                setattr(subject, key, value)
            db.session.commit()
            return redirect(url_for("admin.manage_event_exams", event_id=subject.event_id))

    return render_template(
        "admin/exam_subject_edit.html",
        subject=subject
    )


@admin_bp.route("/admin/subjects/<int:subject_id>/delete", methods=["POST"])
def delete_exam_subject(subject_id):

    if "admin" not in session:
        return redirect(url_for("routes.login"))

    subject = ExamSubject.query.get_or_404(subject_id)
    event_id = subject.event_id
    db.session.delete(subject)
    db.session.commit()

    return redirect(url_for("admin.manage_event_exams", event_id=event_id))


@admin_bp.route("/admin/exams/<int:exam_id>/edit", methods=["GET", "POST"])
def edit_online_exam(exam_id):

    if "admin" not in session:
        return redirect(url_for("routes.login"))

    exam = OnlineExam.query.get_or_404(exam_id)

    if request.method == "POST":
        payload = online_exam_payload_from_form()
        subject = ExamSubject.query.filter_by(
            id=payload["subject_id"],
            event_id=exam.event_id
        ).first()
        existing = OnlineExam.query.filter(
            OnlineExam.exam_code == payload["exam_code"],
            OnlineExam.id != exam.id
        ).first()

        if subject and payload["exam_title"] and payload["exam_code"] and not existing:
            for key, value in payload.items():
                setattr(exam, key, value)
            db.session.commit()
            return redirect(url_for("admin.edit_online_exam", exam_id=exam.id))

    attempts = ExamAttempt.query.filter_by(
        exam_id=exam.id
    ).order_by(ExamAttempt.submitted_at.desc()).all()

    return render_template(
        "admin/exam_edit.html",
        exam=exam,
        subjects=ExamSubject.query.filter_by(event_id=exam.event_id).order_by(ExamSubject.subject_name.asc()).all(),
        answer_option_choices=ANSWER_OPTION_CHOICES,
        question_type_choices=QUESTION_TYPE_CHOICES,
        attempts=attempts
    )


@admin_bp.route("/admin/exams/<int:exam_id>/delete", methods=["POST"])
def delete_online_exam(exam_id):

    if "admin" not in session:
        return redirect(url_for("routes.login"))

    exam = OnlineExam.query.get_or_404(exam_id)
    event_id = exam.event_id
    db.session.delete(exam)
    db.session.commit()

    return redirect(url_for("admin.manage_event_exams", event_id=event_id))


@admin_bp.route("/admin/exams/<int:exam_id>/questions", methods=["POST"])
def add_exam_question(exam_id):

    if "admin" not in session:
        return redirect(url_for("routes.login"))

    exam = OnlineExam.query.get_or_404(exam_id)
    payload = exam_question_payload_from_form()

    is_descriptive = payload["question_type"] == "descriptive"
    options_ready = (
        payload["option_a"] and
        payload["option_b"] and
        payload["option_c"] and
        payload["option_d"]
    )

    if payload["question_text"] and (is_descriptive or options_ready):
        db.session.add(ExamQuestion(exam_id=exam.id, **payload))
        db.session.commit()

    return redirect(url_for("admin.edit_online_exam", exam_id=exam.id))


@admin_bp.route("/admin/questions/<int:question_id>/edit", methods=["GET", "POST"])
def edit_exam_question(question_id):

    if "admin" not in session:
        return redirect(url_for("routes.login"))

    question = ExamQuestion.query.get_or_404(question_id)

    if request.method == "POST":
        payload = exam_question_payload_from_form()
        is_descriptive = payload["question_type"] == "descriptive"
        options_ready = (
            payload["option_a"] and
            payload["option_b"] and
            payload["option_c"] and
            payload["option_d"]
        )
        if payload["question_text"] and (is_descriptive or options_ready):
            for key, value in payload.items():
                setattr(question, key, value)
            db.session.commit()
            return redirect(url_for("admin.edit_online_exam", exam_id=question.exam_id))

    return render_template(
        "admin/exam_question_edit.html",
        question=question,
        answer_option_choices=ANSWER_OPTION_CHOICES,
        question_type_choices=QUESTION_TYPE_CHOICES
    )


@admin_bp.route("/admin/questions/<int:question_id>/delete", methods=["POST"])
def delete_exam_question(question_id):

    if "admin" not in session:
        return redirect(url_for("routes.login"))

    question = ExamQuestion.query.get_or_404(question_id)
    exam_id = question.exam_id
    db.session.delete(question)
    db.session.commit()

    return redirect(url_for("admin.edit_online_exam", exam_id=exam_id))


@admin_bp.route("/admin/exams/<int:exam_id>/results")
def exam_results(exam_id):

    if "admin" not in session:
        return redirect(url_for("routes.login"))

    exam = OnlineExam.query.get_or_404(exam_id)
    attempts = ExamAttempt.query.filter_by(
        exam_id=exam.id
    ).order_by(ExamAttempt.submitted_at.desc()).all()

    return render_template(
        "admin/exam_results.html",
        exam=exam,
        attempts=attempts
    )


@admin_bp.route("/admin/exams/<int:exam_id>/manual-score", methods=["POST"])
def manual_score_exam(exam_id):

    if "admin" not in session:
        return redirect(url_for("routes.login"))

    exam = OnlineExam.query.get_or_404(exam_id)

    for attempt in exam.attempts:
        for answer in attempt.answers:
            field_name = f"manual_score_{answer.id}"
            raw_value = request.form.get(field_name, "").strip()
            if raw_value == "":
                answer.manual_score = None if answer.question and answer.question.question_type == "descriptive" else answer.manual_score
                continue
            try:
                answer.manual_score = float(raw_value)
            except ValueError:
                continue

        recalculate_attempt_scores(attempt)

    db.session.commit()
    return redirect(url_for("admin.exam_results", exam_id=exam.id))


@admin_bp.route("/admin/exams/<int:exam_id>/export-results")
def export_exam_results(exam_id):

    if "admin" not in session:
        return redirect(url_for("routes.login"))

    exam = OnlineExam.query.get_or_404(exam_id)
    attempts = ExamAttempt.query.filter_by(
        exam_id=exam.id
    ).order_by(ExamAttempt.score.desc(), ExamAttempt.submitted_at.asc()).all()

    rows = []
    for index, attempt in enumerate(attempts, start=1):
        rows.append({
            "Rank": index,
            "Participant": attempt.participant.teacher_name if attempt.participant else "",
            "Registration ID": attempt.participant.reg_id if attempt.participant else "",
            "Mobile": attempt.participant.mobile if attempt.participant else "",
            "Score": attempt.score,
            "Total Marks": attempt.total_marks,
            "Correct Answers": attempt.correct_answers,
            "Total Questions": attempt.total_questions,
            "Status": "Passed" if attempt.score >= exam.pass_mark else "Failed",
            "Submitted At": attempt.submitted_at.strftime("%d-%m-%Y %H:%M") if attempt.submitted_at else "",
        })

    df = pd.DataFrame(rows)
    output = BytesIO()
    filename = f"{exam.exam_code}_results.xlsx"
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Results")
    output.seek(0)
    return send_file(output, as_attachment=True, download_name=filename)


@admin_bp.route("/admin/exams/<int:exam_id>/rank-list")
def exam_rank_list(exam_id):

    if "admin" not in session:
        return redirect(url_for("routes.login"))

    exam = OnlineExam.query.get_or_404(exam_id)
    attempts = ExamAttempt.query.filter_by(
        exam_id=exam.id
    ).order_by(ExamAttempt.score.desc(), ExamAttempt.submitted_at.asc()).all()

    top_attempts = attempts[:10]
    return render_template(
        "admin/exam_rank_list.html",
        exam=exam,
        attempts=attempts,
        top_attempts=top_attempts
    )


@admin_bp.route("/admin/exams/<int:exam_id>/import-questions", methods=["POST"])
def import_exam_questions(exam_id):

    if "admin" not in session:
        return redirect(url_for("routes.login"))

    exam = OnlineExam.query.get_or_404(exam_id)
    file = request.files.get("question_file")

    if file and file.filename:
        dataframe = pd.read_excel(file)
        for _, row in dataframe.fillna("").iterrows():
            question_type = str(row.get("question_type", "mcq")).strip().lower() or "mcq"
            question_text = str(row.get("question_text", "")).strip()
            if not question_text:
                continue

            db.session.add(
                ExamQuestion(
                    exam_id=exam.id,
                    question_type=question_type,
                    question_text=question_text,
                    option_a=str(row.get("option_a", "")).strip(),
                    option_b=str(row.get("option_b", "")).strip(),
                    option_c=str(row.get("option_c", "")).strip(),
                    option_d=str(row.get("option_d", "")).strip(),
                    correct_option=str(row.get("correct_option", "")).strip().upper(),
                    model_answer=str(row.get("model_answer", "")).strip(),
                    explanation=str(row.get("explanation", "")).strip(),
                    marks=float(row.get("marks", exam.marks_per_question or 1) or 1),
                    sort_order=int(row.get("sort_order", 0) or 0),
                    is_active=True,
                )
            )

        db.session.commit()

    return redirect(url_for("admin.edit_online_exam", exam_id=exam.id))


@admin_bp.route("/admin/events/<int:event_id>/fields", methods=["POST"])
def add_event_field(event_id):

    if "admin" not in session:
        return redirect(url_for("routes.login"))

    event = Event.query.get_or_404(event_id)
    payload = event_field_payload_from_form()

    if payload["field_label"] and payload["field_name"]:
        exists = EventField.query.filter_by(
            event_id=event.id,
            field_name=payload["field_name"]
        ).first()

        if not exists:
            db.session.add(EventField(event_id=event.id, **payload))
            db.session.commit()

    return redirect(url_for("admin.edit_event", id=event.id))


@admin_bp.route("/admin/events/<int:event_id>/fields/<int:field_id>/edit", methods=["GET", "POST"])
def edit_event_field(event_id, field_id):

    if "admin" not in session:
        return redirect(url_for("routes.login"))

    event = Event.query.get_or_404(event_id)
    field = EventField.query.filter_by(
        id=field_id,
        event_id=event.id
    ).first_or_404()

    if request.method == "POST":
        payload = event_field_payload_from_form()

        existing = EventField.query.filter(
            EventField.event_id == event.id,
            EventField.field_name == payload["field_name"],
            EventField.id != field.id
        ).first()

        if not existing and payload["field_label"] and payload["field_name"]:
            if field.field_name in PROTECTED_FIELD_NAMES:
                payload["field_name"] = field.field_name

            for key, value in payload.items():
                setattr(field, key, value)
            db.session.commit()
            return redirect(url_for("admin.edit_event", id=event.id))

    return render_template(
        "admin/event_field_edit.html",
        event=event,
        field=field,
        field_type_choices=FIELD_TYPE_CHOICES,
        data_type_choices=DATA_TYPE_CHOICES,
        system_field_choices=SYSTEM_FIELD_CHOICES
    )


@admin_bp.route("/admin/events/<int:event_id>/fields/<int:field_id>/delete", methods=["POST"])
def delete_event_field(event_id, field_id):

    if "admin" not in session:
        return redirect(url_for("routes.login"))

    field = EventField.query.filter_by(
        id=field_id,
        event_id=event_id
    ).first_or_404()

    if field.field_name not in PROTECTED_FIELD_NAMES:
        db.session.delete(field)
        db.session.commit()

    return redirect(url_for("admin.edit_event", id=event_id))


@admin_bp.route("/admin/events/<int:id>/toggle-active", methods=["POST"])
def toggle_event_active(id):

    if "admin" not in session:
        return redirect(url_for("routes.login"))

    event = Event.query.get_or_404(id)
    event.is_active = not event.is_active
    db.session.commit()

    return redirect(url_for("admin.events"))


@admin_bp.route("/admin/events/<int:id>/toggle-photo", methods=["POST"])
def toggle_event_photo_rule(id):

    if "admin" not in session:
        return redirect(url_for("routes.login"))

    event = Event.query.get_or_404(id)
    if event.collect_photo:
        event.requires_photo = not event.requires_photo
    db.session.commit()

    return redirect(url_for("admin.events"))

# =====================================================
# DELETE PARTICIPANT
# =====================================================
@admin_bp.route("/delete/<int:id>")
def delete_participant(id):

    if not session.get("admin"):
        return redirect(url_for("routes.login"))

    participant = Participant.query.get_or_404(id)

    db.session.delete(participant)

    db.session.commit()

    return redirect(url_for("admin.admin"))


# =====================================================
# EXPORT EXCEL
# =====================================================
@admin_bp.route("/export")
def export():

    if not session.get("admin"):
        return redirect(url_for("routes.login"))

    events = Event.query.order_by(Event.created_at.desc(), Event.id.desc()).all()
    selected_event_ids = request.args.getlist("event_id", type=int)
    download = request.args.get("download") == "1"

    if not download:
        return render_template(
            "admin/export.html",
            events=events,
            selected_event_ids=selected_event_ids
        )

    query = Participant.query

    if selected_event_ids:
        query = query.filter(Participant.event_id.in_(selected_event_ids))

    participants = query.order_by(
        Participant.event_id.asc(),
        Participant.id.asc()
    ).all()

    data = []

    for p in participants:
        row = {
            "Registration ID": p.reg_id,
            "Event": p.event.name if p.event else "",

            "Salutation": p.salutation,

            "Participant Name": p.teacher_name,

            "Mobile": p.mobile,

            "Email": p.email,

            "Designation": p.designation,

            "Subject": p.subject,

            "School Name": p.school_name,

            "School Area": p.school_area,

            "Block": p.block
        }

        for item in p.extra_data_items():
            row[item["label"]] = item["value"]

        data.append(row)

    df = pd.DataFrame(data)

    if len(selected_event_ids) == 1:
        event = Event.query.get(selected_event_ids[0])
        suffix = event.slug if event else "selected-event"
        filename = f"participants_{suffix}.xlsx"
    elif selected_event_ids:
        filename = "participants_selected_events.xlsx"
    else:
        filename = "participants_all_events.xlsx"

    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Participants")
    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name=filename
    )

# =====================================================
# LOGOUT
# =====================================================
@admin_bp.route("/admin/logout")
def admin_logout():

    session.clear()

    return redirect(url_for("routes.login"))
