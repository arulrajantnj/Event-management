from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    session,
    send_file,
    url_for,
    Response,
)

from sqlalchemy.exc import IntegrityError
from models import (
    db,
    Event,
    EventField,
    ExamAnswer,
    ExamAttempt,
    ExamQuestion,
    OnlineExam,
    Participant,
    Block,
)
from certificate_generator import generate_certificate, get_active_template

from datetime import datetime, timedelta
import qrcode
import json
import os
import re
import uuid
import traceback
from urllib.parse import quote
from werkzeug.security import check_password_hash
from PIL import Image, ImageDraw, ImageFont

# ==========================================================
# Blueprint
# ==========================================================

routes = Blueprint("routes", __name__)

# ==========================================================
# Folders
# ==========================================================

UPLOAD_FOLDER = "static/uploads"
QR_FOLDER = "static/generated_qr"
CERT_FOLDER = "static/generated_certificates"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(QR_FOLDER, exist_ok=True)
os.makedirs(CERT_FOLDER, exist_ok=True)

print("=" * 60)
print("SRI VANDURAI EVENTS")
print("routes.py Loaded Successfully")
print("=" * 60)

CODE39_PATTERNS = {
    "0": "101001101101",
    "1": "110100101011",
    "2": "101100101011",
    "3": "110110010101",
    "4": "101001101011",
    "5": "110100110101",
    "6": "101100110101",
    "7": "101001011011",
    "8": "110100101101",
    "9": "101100101101",
    "A": "110101001011",
    "B": "101101001011",
    "C": "110110100101",
    "D": "101011001011",
    "E": "110101100101",
    "F": "101101100101",
    "G": "101010011011",
    "H": "110101001101",
    "I": "101101001101",
    "J": "101011001101",
    "K": "110101010011",
    "L": "101101010011",
    "M": "110110101001",
    "N": "101011010011",
    "O": "110101101001",
    "P": "101101101001",
    "Q": "101010110011",
    "R": "110101011001",
    "S": "101101011001",
    "T": "101011011001",
    "U": "110010101011",
    "V": "100110101011",
    "W": "110011010101",
    "X": "100101101011",
    "Y": "110010110101",
    "Z": "100110110101",
    "-": "100101011011",
    ".": "110010101101",
    " ": "100110101101",
    "$": "100100100101",
    "/": "100100101001",
    "+": "100101001001",
    "%": "101001001001",
    "*": "100101101101",
}

# ==========================================================
# HOME
# ==========================================================

@routes.route("/")
def home():
    events = Event.query.filter_by(
        is_active=True
    ).order_by(
        Event.created_at.desc(),
        Event.id.desc()
    ).all()
    latest_events = events[:3]
    ticker_messages = [
        event.marquee_message or (
            f"{event.name} service is now available."
            if event.registration_type == "no_registration"
            else f"{event.name} registration is now open."
        )
        for event in events
    ]
    return render_template(
        "index.html",
        events=events,
        latest_events=latest_events,
        registration_events=[
            event
            for event in events
            if event.registration_type != "no_registration"
        ],
        ticker_messages=ticker_messages
    )


@routes.route("/sitemap.xml")
def sitemap():
    base_url = request.host_url.rstrip("/")
    urls = [
        {"loc": f"{base_url}/", "changefreq": "daily", "priority": "1.0"},
        {"loc": f"{base_url}/register", "changefreq": "weekly", "priority": "0.8"},
    ]

    for event in active_events():
        urls.append({
            "loc": f"{base_url}/register?event={quote(event.slug, safe='')}",
            "changefreq": "weekly",
            "priority": "0.7",
        })

    xml_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]

    for item in urls:
        xml_lines.append("  <url>")
        xml_lines.append(f"    <loc>{item['loc']}</loc>")
        xml_lines.append(f"    <changefreq>{item['changefreq']}</changefreq>")
        xml_lines.append(f"    <priority>{item['priority']}</priority>")
        xml_lines.append("  </url>")

    xml_lines.append("</urlset>")
    xml_content = "\n".join(xml_lines)

    return Response(xml_content, mimetype="application/xml")


@routes.route("/robots.txt")
def robots():
    base_url = request.host_url.rstrip("/")
    content = (
        "User-agent: *\n"
        "Allow: /\n"
        f"Sitemap: {base_url}/sitemap.xml\n"
    )
    return Response(content, mimetype="text/plain")


def active_events():
    return Event.query.filter_by(
        is_active=True
    ).order_by(
        Event.created_at.desc(),
        Event.id.desc()
    ).all()


def registration_events():
    return [
        event
        for event in active_events()
        if event.registration_type != "no_registration"
    ]


def selected_event_or_default(event_slug=None):
    events = registration_events()
    if not events:
        return [], None

    if event_slug:
        for event in events:
            if event.slug == event_slug:
                return events, event

    return events, events[0]


def current_certificate_image():
    active_template = get_active_template()

    if active_template and active_template.image_path:
        return f"certificate_templates/{active_template.image_path}"

    return None


SYSTEM_FIELD_NAMES = {
    "salutation",
    "teacher_name",
    "mobile",
    "email",
    "designation",
    "subject",
    "school_name",
    "school_area",
    "block",
}


def registration_fields_for_event(event):
    fields = [
        field
        for field in event.registration_fields
        if field.is_active
    ]

    return sorted(
        fields,
        key=lambda item: (item.sort_order or 0, item.id or 0)
    )


def serialize_field(field):
    return {
        "field_name": field.field_name,
        "field_label": field.field_label,
        "field_type": field.field_type,
        "data_type": field.data_type,
        "placeholder": field.placeholder or "",
        "options": field.options_list(),
        "help_text": field.help_text or "",
        "is_required": bool(field.is_required),
    }


def display_value_for_field(field, value):
    if field.field_name == "mobile":
        return value
    return value.strip() if isinstance(value, str) else value


def registration_field_payload(event):
    return [
        serialize_field(field)
        for field in registration_fields_for_event(event)
    ]


def event_field_state(event):
    fields = registration_field_payload(event)
    available_field_names = {
        field["field_name"]
        for field in fields
    }

    return {
        "collect_photo": bool(event.collect_photo),
        "requires_photo": bool(event.collect_photo and event.requires_photo),
        "registration_fields": fields,
        "field_names": available_field_names,
        "payment_enabled": bool(event.payment_enabled),
        "whatsapp_ack_enabled": bool(event.whatsapp_ack_enabled),
        "whatsapp_group_enabled": bool(event.whatsapp_group_enabled),
        "acknowledgement_enabled": bool(event.acknowledgement_enabled),
        "certificate_enabled": bool(event.certificate_enabled),
        "qr_sharing_enabled": bool(event.qr_sharing_enabled),
    }


def participant_display_rows(field_payload, submitted_values):
    rows = []

    for field in field_payload:
        value = submitted_values.get(field["field_name"], "")
        if value not in ("", None):
            rows.append({
                "field_name": field["field_name"],
                "label": field["field_label"],
                "value": value
            })

    return rows


def validate_registration_fields(event, field_payload):
    values = {}
    extra_data = {}
    errors = []

    for field in field_payload:
        raw_value = request.form.get(field["field_name"], "")
        value = raw_value.strip() if isinstance(raw_value, str) else raw_value
        values[field["field_name"]] = value

        if field["is_required"] and not value:
            errors.append(f"{field['field_label']} is required.")
            continue

        if not value:
            continue

        if field["field_type"] == "select" and field["options"] and value not in field["options"]:
            errors.append(f"Please choose a valid option for {field['field_label']}.")

        if field["field_type"] == "email":
            if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
                errors.append("Please enter a valid email address.")

        if field["field_name"] == "mobile":
            if not re.fullmatch(r"[6-9][0-9]{9}", value):
                errors.append("Please enter a valid 10-digit mobile number.")

        if field["data_type"] == "integer" and value:
            if not re.fullmatch(r"\d+", value):
                errors.append(f"{field['field_label']} must be a whole number.")

        if field["data_type"] == "decimal" and value:
            if not re.fullmatch(r"\d+(\.\d+)?", value):
                errors.append(f"{field['field_label']} must be a valid number.")

        if field["field_name"] not in SYSTEM_FIELD_NAMES:
            extra_data[field["field_name"]] = {
                "label": field["field_label"],
                "value": value
            }

    return values, extra_data, errors


def whatsapp_ack_link(event, participant):
    if not event or not event.whatsapp_ack_enabled or not participant.mobile:
        return ""

    template = (
        event.whatsapp_template
        or "Your registration for {event_name} is confirmed. Reg ID: {reg_id}."
    )
    message = template.format(
        event_name=event.name,
        reg_id=participant.reg_id,
        participant_name=participant.teacher_name
    )
    return f"https://wa.me/91{participant.mobile}?text={quote(message)}"


def selected_code_fields(event):
    raw_fields = (event.code_fields or "").splitlines() if event else []
    fields = [item.strip() for item in raw_fields if item.strip()]
    return fields or ["attendance_url", "reg_id", "participant_name", "event_name"]


def registration_id_for_event(event):
    prefix = re.sub(r"[^A-Z0-9-]+", "", (event.reg_id_prefix or "EVT").upper()) or "EVT"
    padding = min(max(int(event.reg_id_padding or 4), 1), 10)
    next_number = max(int(event.reg_id_next_number or 1), 1)

    for serial_number in range(next_number, next_number + 1000):
        reg_id = f"{prefix}{serial_number:0{padding}d}"
        if not Participant.query.filter_by(reg_id=reg_id).first():
            event.reg_id_next_number = serial_number + 1
            return reg_id

    fallback = f"{prefix}{uuid.uuid4().hex[:8].upper()}"
    event.reg_id_next_number = next_number + 1000
    return fallback[:30]


def participant_code_values(event, participant):
    return {
        "attendance_url": url_for(
            "admin.mark_attendance",
            reg_id=participant.reg_id,
            _external=True
        ),
        "reg_id": participant.reg_id,
        "event_name": event.name if event else "",
        "participant_name": participant.teacher_name or "",
        "mobile": participant.mobile or "",
        "email": participant.email or "",
        "designation": participant.designation or "",
        "subject": participant.subject or "",
        "school_name": participant.school_name or "",
        "school_area": participant.school_area or "",
        "block": participant.block or "",
    }


def code_payload_for_participant(event, participant):
    values = participant_code_values(event, participant)
    lines = []

    for field_name in selected_code_fields(event):
        value = values.get(field_name, "")
        if value:
            if field_name == "attendance_url":
                lines.append(value)
                continue
            label = field_name.replace("_", " ").title()
            lines.append(f"{label}: {value}")

    return "\n".join(lines) or participant.reg_id


def render_code39_barcode(value, path):
    safe_value = "".join(
        char for char in (value or "").upper()
        if char in CODE39_PATTERNS and char != "*"
    ) or "INVALID"
    encoded = f"*{safe_value}*"
    bar_width = 3
    wide_multiplier = 3
    gap = bar_width
    height = 110
    quiet = 24
    text_height = 32

    width = quiet * 2
    for char in encoded:
        pattern = CODE39_PATTERNS[char]
        width += sum((wide_multiplier if bit == "1" else 1) * bar_width for bit in pattern) + gap

    image = Image.new("RGB", (width, height + text_height), "white")
    draw = ImageDraw.Draw(image)
    x = quiet

    for char in encoded:
        pattern = CODE39_PATTERNS[char]
        for index, bit in enumerate(pattern):
            element_width = (wide_multiplier if bit == "1" else 1) * bar_width
            if index % 2 == 0:
                draw.rectangle([x, 10, x + element_width - 1, height], fill="black")
            x += element_width
        x += gap

    try:
        font = ImageFont.truetype("arial.ttf", 18)
    except OSError:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), safe_value, font=font)
    text_width = bbox[2] - bbox[0]
    draw.text(((width - text_width) / 2, height + 6), safe_value, fill="black", font=font)
    image.save(path)


def generate_participant_code(event, participant):
    filename = f"{participant.reg_id}.png"
    path = os.path.join(QR_FOLDER, filename)

    if event and event.code_type == "barcode":
        render_code39_barcode(participant.reg_id, path)
    else:
        qr = qrcode.make(code_payload_for_participant(event, participant))
        qr.save(path)

    participant.qr_code = os.path.join("generated_qr", filename)
    return path


def current_exam_participant():
    participant_id = session.get("exam_participant_id")
    if not participant_id:
        return None

    return Participant.query.get(participant_id)


def exam_time_status(exam):
    now = datetime.utcnow()
    if exam.start_at and now < exam.start_at:
        return "upcoming"
    if exam.end_at and now > exam.end_at:
        return "closed"
    return "open"


def exam_deadline(exam, started_at):
    if not started_at:
        return exam.end_at

    deadline = started_at
    if exam.duration_minutes:
        deadline = started_at + timedelta(minutes=exam.duration_minutes)

    if exam.end_at and exam.end_at < deadline:
        return exam.end_at

    return deadline


def recalculate_attempt_scores(attempt):
    total_marks = 0.0
    score = 0.0
    correct_answers = 0
    pending = False

    for answer in attempt.answers:
        question = answer.question
        if not question:
            continue

        question_marks = float(question.marks or 0)
        total_marks += question_marks
        awarded = answer.awarded_score
        score += awarded

        if question.question_type == "descriptive":
            if answer.manual_score is None:
                pending = True
        elif answer.is_correct:
            correct_answers += 1

    attempt.total_marks = total_marks
    attempt.score = score
    attempt.correct_answers = correct_answers
    attempt.total_questions = len(attempt.answers)
    attempt.evaluation_status = "pending_review" if pending else "evaluated"


# ==========================================================
# REGISTER
# ==========================================================

@routes.route("/register", methods=["GET", "POST"])
def register():
    requested_slug = request.args.get("event", "").strip()
    events, selected_event = selected_event_or_default(requested_slug)

    if not selected_event:
        return render_template(
            "register.html",
            error="No active events are available for registration right now.",
            events=[],
            selected_event=None,
            selected_event_slug="",
            certificate_image=current_certificate_image(),
            field_state={},
            event_fields=[],
            form_values={},
        )

    if request.method == "POST":
        event_slug = request.form.get("event_slug", "").strip()
        events, selected_event = selected_event_or_default(event_slug)

        if not selected_event:
            return render_template(
                "register.html",
                error="Please choose a valid event.",
                events=events,
                selected_event=None,
                selected_event_slug=event_slug,
                certificate_image=current_certificate_image(),
                field_state={},
                event_fields=[],
                form_values=request.form,
            )

        field_state = event_field_state(selected_event)
        event_fields = field_state["registration_fields"]
        field_values, extra_data, validation_errors = validate_registration_fields(
            selected_event,
            event_fields
        )

        teacher_name = field_values.get("teacher_name", "").strip()
        mobile = field_values.get("mobile", "").strip()
        email = field_values.get("email", "").strip()
        designation = field_values.get("designation", "").strip()
        subject = field_values.get("subject", "").strip()
        school_name = field_values.get("school_name", "").strip()
        school_area = field_values.get("school_area", "").strip()
        block = field_values.get("block", "").strip()
        salutation = field_values.get("salutation", "").strip()

        # -----------------------------
        # Validation
        # -----------------------------

        if validation_errors:
            return render_template(
                "register.html",
                error=validation_errors[0],
                events=events,
                selected_event=selected_event,
                selected_event_slug=selected_event.slug,
                certificate_image=current_certificate_image(),
                field_state=field_state,
                event_fields=event_fields,
                form_values=request.form,
            )

        existing = Participant.query.filter_by(
            event_id=selected_event.id,
            mobile=mobile
        ).first()

        if existing:

            return render_template(
                "register.html",
                error=f"This mobile number is already registered for {selected_event.name}.",
                events=events,
                selected_event=selected_event,
                selected_event_slug=selected_event.slug,
                certificate_image=current_certificate_image(),
                field_state=field_state,
                event_fields=event_fields,
                form_values=request.form,
            )

        # -----------------------------
        # Upload Teacher Photo
        # -----------------------------

        photo = request.files.get("photo")
        filename = ""

        if field_state["collect_photo"] and photo and photo.filename != "":

            ext = photo.filename.rsplit(".", 1)[-1].lower()

            filename = (
                mobile
                + "_"
                + uuid.uuid4().hex[:8]
                + "."
                + ext
            )

            photo.save(
                os.path.join(
                    UPLOAD_FOLDER,
                    filename
                )
            )

        if field_state["requires_photo"] and not filename:
            return render_template(
                "register.html",
                error=f"{selected_event.name} requires a photo upload.",
                events=events,
                selected_event=selected_event,
                selected_event_slug=selected_event.slug,
                certificate_image=current_certificate_image(),
                field_state=field_state,
                event_fields=event_fields,
                form_values=request.form,
            )

        # -----------------------------
        # Store in Session
        # -----------------------------

        session["registration"] = {
            "event_id": selected_event.id,

            "event_name": selected_event.name,

            "event_slug": selected_event.slug,

            "event_requires_photo": selected_event.requires_photo,
            "event_collect_photo": field_state["collect_photo"],
            "event_payment_enabled": bool(selected_event.payment_enabled),
            "event_payment_amount": selected_event.payment_amount or 0,
            "event_payment_link": selected_event.payment_link or "",
            "event_payment_notes": selected_event.payment_notes or "",
            "event_whatsapp_ack_enabled": bool(selected_event.whatsapp_ack_enabled),
            "event_whatsapp_group_enabled": bool(selected_event.whatsapp_group_enabled),
            "event_whatsapp_group_link": selected_event.whatsapp_group_link or "",
            "event_acknowledgement_enabled": bool(selected_event.acknowledgement_enabled),
            "event_certificate_enabled": bool(selected_event.certificate_enabled),
            "event_qr_sharing_enabled": bool(selected_event.qr_sharing_enabled),
            "event_fields": event_fields,
            "field_values": field_values,

            "salutation": salutation,

            "teacher_name": teacher_name,

            "mobile": mobile,

            "email": email,

            "designation": designation,

            "subject": subject,

            "school_name": school_name,

            "school_area": school_area,

            "block": block,

            "extra_data": extra_data,
            "display_rows": participant_display_rows(event_fields, field_values),
            "photo": filename

        }

        return redirect(url_for("routes.preview"))

    return render_template(
        "register.html",
        events=events,
        selected_event=selected_event,
        selected_event_slug=selected_event.slug,
        certificate_image=current_certificate_image(),
        field_state=event_field_state(selected_event),
        event_fields=registration_field_payload(selected_event),
        form_values={},
    )
# ==========================================================
# PREVIEW
# ==========================================================
@routes.route("/preview")
def preview():

    if "registration" not in session:
        return redirect(url_for("routes.register"))

    participant = session["registration"].copy()
    event = Event.query.get(participant["event_id"])

    # temp preview ID
    participant["reg_id"] = f"PREVIEW{uuid.uuid4().hex[:6].upper()}"

    issue_date = datetime.today().strftime("%d-%m-%Y")

    # TEMPLATE
    active_template = get_active_template()
    template_image = "certificate_templates/winner.png"

    if active_template and active_template.image_path:
        template_image = f"certificate_templates/{active_template.image_path}"

    # QR for preview
    qr = qrcode.make(participant["reg_id"])
    qr.save(os.path.join(QR_FOLDER, "preview_qr.png"))

    return render_template(
        "preview.html",
        participant=participant,
        event=event,
        issue_date=issue_date,
        template_image=template_image
    )


# ==========================================================
# CONFIRM REGISTRATION
# ==========================================================
@routes.route("/confirm-registration", methods=["POST"])
def confirm_registration():

    if "registration" not in session:
        return redirect(url_for("routes.register"))

    data = session["registration"]
    event = Event.query.get(data["event_id"])

    if not event or not event.is_active:
        session.pop("registration", None)
        return redirect(url_for("routes.register"))

    existing = Participant.query.filter_by(
        event_id=event.id,
        mobile=data["mobile"]
    ).first()

    if existing:
        session.pop("registration", None)
        return render_template(
            "register.html",
            error=f"This mobile number is already registered for {event.name}.",
            events=active_events(),
            selected_event=event,
            selected_event_slug=event.slug,
            certificate_image=current_certificate_image(),
            field_state=event_field_state(event),
            event_fields=registration_field_payload(event),
            form_values=data.get("field_values", data),
        )

    reg_id = registration_id_for_event(event)

    participant = Participant(
        reg_id=reg_id,
        event_id=event.id,
        salutation=data.get("salutation", ""),
        teacher_name=data["teacher_name"],
        mobile=data["mobile"],
        email=data["email"],
        designation=data["designation"],
        subject=data["subject"],
        school_name=data["school_name"],
        school_area=data["school_area"],
        block=data["block"],
        photo=data["photo"],
        extra_data=json.dumps(data.get("extra_data", {}))
    )

    print("=" * 60)
    print("NEW REGISTRATION")
    print("Teacher :", participant.teacher_name)
    print("School  :", participant.school_name)
    print("Photo   :", participant.photo)
    print("=" * 60)

    db.session.add(participant)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        session.pop("registration", None)
        return render_template(
            "register.html",
            error=f"Duplicate registration detected. This mobile number is already registered for {event.name}.",
            events=active_events(),
            selected_event=event,
            selected_event_slug=event.slug,
            certificate_image=current_certificate_image(),
            field_state=event_field_state(event),
            event_fields=registration_field_payload(event),
            form_values=data.get("field_values", data),
        )

    # --------------------------------------------
    # Generate QR Code
    # --------------------------------------------
    generate_participant_code(event, participant)
    db.session.commit()

    if event.certificate_enabled:
        try:

            # ----------------------------------------
            # Generate Certificate
            # ----------------------------------------
            certificate_file = generate_certificate(participant)
            if not certificate_file.get("success"):
                raise RuntimeError(
                    certificate_file.get("error", "certificate_generation_failed")
                )
            print("Certificate Generated :", certificate_file)

            db.session.commit()

            print("Registration Completed Successfully")

        except Exception as e:

            print("=" * 60)
            print("CERTIFICATE ERROR")
            traceback.print_exc()
            print("=" * 60)

            return f"<h2>Error</h2><pre>{e}</pre>", 500
    else:
        print("Certificate generation skipped for this event")

    session.pop("registration", None)

    return render_template(
        "success.html",
        participant=participant,
        whatsapp_link=whatsapp_ack_link(event, participant)
    )
# ==========================================================
# QR IMAGE
# ==========================================================
@routes.route("/qrcode/<reg_id>")
def qrcode_image(reg_id):

    participant = Participant.query.filter_by(reg_id=reg_id).first()
    if participant and participant.event and not participant.event.qr_sharing_enabled:
        return "QR code sharing is not enabled for this event.", 403

    filepath = os.path.join(QR_FOLDER, f"{reg_id}.png")

    if participant and participant.event and not os.path.exists(filepath):
        generate_participant_code(participant.event, participant)
        db.session.commit()

    if not os.path.exists(filepath):
        return "Code image not found"

    return send_file(filepath, mimetype="image/png")


# ==========================================================
# DOWNLOAD CERTIFICATE
# ==========================================================
@routes.route("/download-certificate/<reg_id>")
def download_certificate(reg_id):

    filepath = os.path.join(
        "static",
        "generated_certificates",
        f"{reg_id}.png"
    )

    if not os.path.exists(filepath):
        return "Certificate not found"

    return send_file(filepath, as_attachment=True)


@routes.route("/downloads", methods=["GET", "POST"])
def downloads():
    participant = None
    searched = False
    error = ""

    if request.method == "POST":
        searched = True
        reg_id = request.form.get("reg_id", "").strip().upper()
        mobile = request.form.get("mobile", "").strip()

        if not reg_id and not mobile:
            error = "Enter your Registration ID or Mobile Number."
        else:
            query = Participant.query

            if reg_id:
                query = query.filter(Participant.reg_id == reg_id)

            if mobile:
                query = query.filter(Participant.mobile == mobile)

            participant = query.order_by(Participant.created_at.desc()).first()

    certificate_ready = bool(
        participant
        and participant.event
        and participant.event.certificate_enabled
    )

    return render_template(
        "downloads.html",
        participant=participant,
        searched=searched,
        error=error,
        certificate_ready=certificate_ready,
    )


@routes.route("/download-certificate-secure", methods=["POST"])
def download_certificate_secure():
    reg_id = request.form.get("reg_id", "").strip().upper()
    mobile = request.form.get("mobile", "").strip()

    participant = Participant.query.filter_by(
        reg_id=reg_id,
        mobile=mobile
    ).first()

    if not participant:
        return render_template(
            "downloads.html",
            participant=None,
            searched=True,
            error="No matching registration was found.",
            certificate_ready=False,
        )

    if not participant.event or not participant.event.certificate_enabled:
        return render_template(
            "downloads.html",
            participant=participant,
            searched=True,
            error="Certificate download is not enabled for this event.",
            certificate_ready=False,
        )

    result = generate_certificate(participant)

    if not result.get("success"):
        return render_template(
            "downloads.html",
            participant=participant,
            searched=True,
            error=result.get("error", "Certificate is not available yet."),
            certificate_ready=False,
        )

    participant.download_count = (participant.download_count or 0) + 1
    participant.last_download = datetime.utcnow()
    participant.certificate_generated = True
    db.session.commit()

    filepath = result.get("certificate_path") or os.path.join(
        "static",
        "generated_certificates",
        f"{participant.reg_id}.png"
    )

    return send_file(filepath, as_attachment=True)


# ==========================================================
# CERTIFICATE PAGE (FIXED)
# ==========================================================
@routes.route("/certificate/<int:id>")
def certificate(id):

    participant = Participant.query.get_or_404(id)

    if not participant.event or not participant.event.certificate_enabled:
        return "Certificate download is not enabled for this event.", 403

    try:
        result = generate_certificate(participant)

        if not result.get("success"):
            raise RuntimeError(result.get("error", "certificate_generation_failed"))

        filepath = result.get("certificate_path")
        if not filepath:
            filepath = os.path.join("static", "generated_certificates", f"{participant.reg_id}.png")

        return send_file(filepath, as_attachment=True)

    except Exception as e:
        return f"Error: {e}", 500


# ==========================================================
# EXAM LOGIN
# ==========================================================
@routes.route("/exam-login", methods=["GET", "POST"])
def exam_login():

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        participant = Participant.query.filter_by(
            exam_username=username
        ).first()

        if (
            not participant
            or not participant.exam_password_hash
            or not check_password_hash(participant.exam_password_hash, password)
            or not participant.event
            or not participant.event.exam_enabled
        ):
            return render_template(
                "exam_login.html",
                error="Invalid username, password, or exam access is not enabled for this event."
            )

        session["exam_participant_id"] = participant.id
        return redirect(url_for("routes.my_exams"))

    return render_template("exam_login.html")


@routes.route("/my-exams")
def my_exams():

    participant = current_exam_participant()
    if not participant:
        return redirect(url_for("routes.exam_login"))

    event = participant.event
    if not event or not event.exam_enabled:
        session.pop("exam_participant_id", None)
        return redirect(url_for("routes.exam_login"))

    exams = OnlineExam.query.filter_by(
        event_id=event.id,
        is_active=True
    ).order_by(
        OnlineExam.created_at.desc()
    ).all()

    attempts = {
        attempt.exam_id: attempt
        for attempt in ExamAttempt.query.filter_by(
            participant_id=participant.id
        ).all()
    }

    exam_status_map = {
        exam.id: exam_time_status(exam)
        for exam in exams
    }

    return render_template(
        "my_exams.html",
        participant=participant,
        event=event,
        exams=exams,
        attempts=attempts,
        exam_status_map=exam_status_map
    )


@routes.route("/exam/<int:exam_id>")
def take_exam(exam_id):

    participant = current_exam_participant()
    if not participant:
        return redirect(url_for("routes.exam_login"))

    exam = OnlineExam.query.get_or_404(exam_id)

    if (
        not exam.is_active or
        exam.event_id != participant.event_id or
        not participant.event.exam_enabled or
        exam_time_status(exam) != "open"
    ):
        return redirect(url_for("routes.my_exams"))

    submitted_attempts = ExamAttempt.query.filter_by(
        exam_id=exam.id,
        participant_id=participant.id
    ).order_by(ExamAttempt.submitted_at.desc()).all()

    if len(submitted_attempts) >= (exam.max_attempts or 1):
        return redirect(
            url_for(
                "routes.exam_result",
                attempt_id=submitted_attempts[0].id
            )
        )

    questions = [
        question
        for question in exam.questions
        if question.is_active
    ]

    start_session_key = f"exam_started_at_{exam.id}"
    started_at_raw = session.get(start_session_key)
    started_at = None

    if started_at_raw:
        try:
            started_at = datetime.fromisoformat(started_at_raw)
        except ValueError:
            started_at = None

    if not started_at:
        started_at = datetime.utcnow()
        session[start_session_key] = started_at.isoformat()
        session.modified = True

    deadline_at = exam_deadline(exam, started_at)

    return render_template(
        "take_exam.html",
        participant=participant,
        exam=exam,
        questions=questions,
        started_at=started_at,
        deadline_at=deadline_at,
        server_now=datetime.utcnow(),
    )


@routes.route("/exam/<int:exam_id>/submit", methods=["POST"])
def submit_exam(exam_id):

    participant = current_exam_participant()
    if not participant:
        return redirect(url_for("routes.exam_login"))

    exam = OnlineExam.query.get_or_404(exam_id)
    if not exam.is_active or exam.event_id != participant.event_id:
        return redirect(url_for("routes.my_exams"))

    if exam_time_status(exam) == "upcoming":
        return redirect(url_for("routes.my_exams"))

    attempt_count = ExamAttempt.query.filter_by(
        exam_id=exam.id,
        participant_id=participant.id
    ).count()

    if attempt_count >= (exam.max_attempts or 1):
        latest_attempt = ExamAttempt.query.filter_by(
            exam_id=exam.id,
            participant_id=participant.id
        ).order_by(ExamAttempt.submitted_at.desc()).first()
        if latest_attempt:
            return redirect(url_for("routes.exam_result", attempt_id=latest_attempt.id))
        return redirect(url_for("routes.my_exams"))

    questions = [
        question
        for question in exam.questions
        if question.is_active
    ]

    start_session_key = f"exam_started_at_{exam.id}"
    started_at_raw = session.get(start_session_key)
    started_at = None
    if started_at_raw:
        try:
            started_at = datetime.fromisoformat(started_at_raw)
        except ValueError:
            started_at = None

    if not started_at:
        started_at = datetime.utcnow()

    deadline_at = exam_deadline(exam, started_at)
    submitted_at = datetime.utcnow()

    if exam.end_at and submitted_at > exam.end_at and deadline_at and deadline_at <= exam.end_at:
        submitted_at = exam.end_at

    violation_count = request.form.get("violation_count", 0, type=int) or 0
    if exam.auto_submit_on_violation and violation_count > (exam.tab_switch_limit or 0):
        violation_count = exam.tab_switch_limit or violation_count

    answers_map = {}
    evaluation_status = "evaluated"

    attempt = ExamAttempt(
        exam_id=exam.id,
        participant_id=participant.id,
        started_at=started_at,
        score=0,
        total_marks=0,
        total_questions=len(questions),
        correct_answers=0,
        evaluation_status=evaluation_status,
        violation_count=violation_count,
        answers_json="{}",
        submitted_at=submitted_at,
    )

    db.session.add(attempt)
    db.session.flush()

    for question in questions:
        if question.question_type == "descriptive":
            text_answer = request.form.get(f"question_{question.id}", "").strip()
            answers_map[str(question.id)] = text_answer
            db.session.add(
                ExamAnswer(
                    attempt_id=attempt.id,
                    question_id=question.id,
                    text_answer=text_answer,
                    auto_score=0,
                    manual_score=None
                )
            )
            attempt.evaluation_status = "pending_review"
            continue

        selected_option = request.form.get(f"question_{question.id}", "").strip().upper()
        is_correct = bool(selected_option and selected_option == (question.correct_option or "").upper())
        awarded = float(question.marks or exam.marks_per_question or 1) if is_correct else -float(exam.negative_marks or 0)
        answers_map[str(question.id)] = selected_option
        db.session.add(
            ExamAnswer(
                attempt_id=attempt.id,
                question_id=question.id,
                selected_option=selected_option,
                is_correct=is_correct,
                auto_score=awarded
            )
        )

    attempt.answers_json = json.dumps(answers_map)
    db.session.flush()
    recalculate_attempt_scores(attempt)
    db.session.commit()
    session.pop(start_session_key, None)

    return redirect(url_for("routes.exam_result", attempt_id=attempt.id))


@routes.route("/exam-result/<int:attempt_id>")
def exam_result(attempt_id):

    participant = current_exam_participant()
    if not participant:
        return redirect(url_for("routes.exam_login"))

    attempt = ExamAttempt.query.get_or_404(attempt_id)
    if attempt.participant_id != participant.id:
        return redirect(url_for("routes.my_exams"))

    exam = attempt.exam
    answer_lookup = attempt.answers_map()
    questions = [
        question
        for question in exam.questions
        if question.is_active
    ]

    return render_template(
        "exam_result.html",
        participant=participant,
        attempt=attempt,
        exam=exam,
        questions=questions,
        answer_lookup=answer_lookup
    )


@routes.route("/hall-ticket/<int:exam_id>")
def hall_ticket(exam_id):

    participant = current_exam_participant()
    if not participant:
        return redirect(url_for("routes.exam_login"))

    exam = OnlineExam.query.get_or_404(exam_id)
    if exam.event_id != participant.event_id:
        return redirect(url_for("routes.my_exams"))

    return render_template(
        "hall_ticket.html",
        participant=participant,
        exam=exam
    )


@routes.route("/exam-logout")
def exam_logout():
    session.pop("exam_participant_id", None)
    return redirect(url_for("routes.exam_login"))

# ==========================================================
# LOGIN
# ==========================================================
@routes.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get("username")
        password = request.form.get("password")

        if username == "Arulrajan" and password == "Arulabisri@1623":
            session["admin"] = True
            return redirect(url_for("admin.admin"))

        return render_template(
            "login.html",
            error="Invalid Username or Password"
        )

    return render_template("login.html")
# ==========================================================
# LOGOUT
# ==========================================================
@routes.route("/logout")
def logout():
    session.clear()
    return redirect("/")
