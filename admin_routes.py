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
)
from datetime import datetime
from io import BytesIO
import pandas as pd
import re


admin_bp = Blueprint("admin", __name__)

REGISTRATION_TYPE_CHOICES = [
    ("teacher", "Teachers"),
    ("student", "Students"),
    ("public", "Common Public"),
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


def checkbox_value(name):
    return name in request.form


def normalize_field_name(value):
    cleaned = re.sub(r"[^a-z0-9_]+", "_", (value or "").strip().lower())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    if not cleaned:
        cleaned = "custom_field"
    if cleaned[0].isdigit():
        cleaned = f"field_{cleaned}"
    return cleaned


def default_fields_for_type(registration_type):
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


def event_payload_from_form():
    collect_photo = checkbox_value("collect_photo")
    payment_enabled = checkbox_value("payment_enabled")
    payment_amount_raw = request.form.get("payment_amount", "").strip()

    try:
        payment_amount = float(payment_amount_raw) if payment_amount_raw else 0
    except ValueError:
        payment_amount = 0

    return {
        "name": request.form.get("name", "").strip(),
        "slug": request.form.get("slug", "").strip(),
        "description": request.form.get("description", "").strip(),
        "registration_type": request.form.get("registration_type", "teacher").strip() or "teacher",
        "collect_photo": collect_photo,
        "requires_photo": collect_photo and checkbox_value("requires_photo"),
        "collect_email": True,
        "collect_designation": True,
        "collect_subject": True,
        "collect_school_name": True,
        "collect_school_area": True,
        "collect_block": True,
        "marquee_message": request.form.get("marquee_message", "").strip(),
        "payment_enabled": payment_enabled,
        "payment_amount": payment_amount,
        "payment_link": request.form.get("payment_link", "").strip(),
        "payment_notes": request.form.get("payment_notes", "").strip(),
        "whatsapp_ack_enabled": checkbox_value("whatsapp_ack_enabled"),
        "whatsapp_template": request.form.get("whatsapp_template", "").strip(),
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
            (Participant.reg_id.contains(search))
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
        registration_type_choices=REGISTRATION_TYPE_CHOICES
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
        payload = event_payload_from_form()

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
        system_field_choices=SYSTEM_FIELD_CHOICES
    )


@admin_bp.route("/admin/exams")
def exams_dashboard():

    if "admin" not in session:
        return redirect(url_for("routes.login"))

    events = Event.query.order_by(
        Event.exam_enabled.desc(),
        Event.created_at.desc(),
        Event.id.desc()
    ).all()

    return render_template(
        "admin/exams_dashboard.html",
        events=events
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

    participants = Participant.query.order_by(
        Participant.id
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

    filename = "participants.xlsx"

    df.to_excel(filename, index=False)

    return send_file(
        filename,
        as_attachment=True
    )

# =====================================================
# LOGOUT
# =====================================================
@admin_bp.route("/admin/logout")
def admin_logout():

    session.clear()

    return redirect(url_for("routes.login"))
