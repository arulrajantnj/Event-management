from flask import Flask
import os
from urllib.parse import quote_plus

from flask_migrate import Migrate

from models import db, Block, Event, EventField

from routes import routes as routes_bp
from admin_routes import admin_bp
from layout_editor import layout_bp

# ==========================
# Create Flask App
# ==========================

app = Flask(__name__)

app.secret_key = "event_management_secret_key"

# ==========================
# Database
# ==========================

os.makedirs(app.instance_path, exist_ok=True)


def database_uri_from_env():
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        if database_url.startswith("mysql://"):
            return database_url.replace("mysql://", "mysql+pymysql://", 1)
        return database_url

    mysql_user = os.getenv("MYSQL_USER", "root")
    mysql_password = quote_plus(os.getenv("MYSQL_PASSWORD", ""))
    mysql_host = os.getenv("MYSQL_HOST", "localhost")
    mysql_port = os.getenv("MYSQL_PORT", "3306")
    mysql_database = os.getenv("MYSQL_DATABASE", "event_management")
    credentials = mysql_user
    if mysql_password:
        credentials = f"{credentials}:{mysql_password}"

    return (
        f"mysql+pymysql://{credentials}@{mysql_host}:{mysql_port}/"
        f"{mysql_database}?charset=utf8mb4"
    )


app.config["SQLALCHEMY_DATABASE_URI"] = database_uri_from_env()
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_pre_ping": True,
    "pool_recycle": 280,
}

# ==========================
# Upload Folder
# ==========================

app.config["UPLOAD_FOLDER"] = "static/certificate_templates"

os.makedirs("static/certificate_templates", exist_ok=True)
# Generated Files
os.makedirs("static/generated_certificates", exist_ok=True)
os.makedirs("static/generated_qr", exist_ok=True)
os.makedirs("static/uploads", exist_ok=True)
os.makedirs("qrcodes", exist_ok=True)

# ==========================
# Initialize Database
# ==========================

db.init_app(app)
migrate = Migrate(app, db)


# ==========================
# Register Blueprints
# ==========================

app.register_blueprint(routes_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(layout_bp)

@app.errorhandler(500)
def internal_server_error(error):
    import traceback

    tb = traceback.format_exc()
    print("===== INTERNAL SERVER ERROR =====")
    print(tb)
    print("=================================")
    return f"<h1>Internal Server Error</h1><pre>{tb}</pre>", 500

# ==========================
# Create Database Tables
# ==========================

DEFAULT_EVENTS = [
    {
        "name": "100% Pass Teachers Felicitation Programme",
        "slug": "teachers-felicitation-2026",
        "description": "Certificate-based teacher felicitation event with photo-enabled registration.",
        "registration_type": "teacher",
        "collect_photo": True,
        "requires_photo": True,
        "collect_email": True,
        "collect_designation": True,
        "collect_subject": True,
        "collect_school_name": True,
        "collect_school_area": True,
        "collect_block": True,
        "marquee_message": "Teacher felicitation registrations are open now with certificate support.",
        "payment_enabled": False,
        "payment_amount": 0,
        "payment_link": "",
        "payment_notes": "",
        "whatsapp_ack_enabled": True,
        "whatsapp_template": "Your registration for {event_name} is confirmed. Reg ID: {reg_id}.",
        "qr_sharing_enabled": True,
        "exam_enabled": False,
        "is_active": True,
    },
    {
        "name": "School Leadership Workshop",
        "slug": "school-leadership-workshop",
        "description": "Workshop registration without mandatory photo upload.",
        "registration_type": "teacher",
        "collect_photo": False,
        "requires_photo": False,
        "collect_email": True,
        "collect_designation": True,
        "collect_subject": False,
        "collect_school_name": True,
        "collect_school_area": False,
        "collect_block": False,
        "marquee_message": "Leadership workshop registrations are now live. Photo upload is not required.",
        "payment_enabled": True,
        "payment_amount": 250,
        "payment_link": "https://example.com/pay/school-leadership-workshop",
        "payment_notes": "Workshop participation fee can be collected online after registration.",
        "whatsapp_ack_enabled": True,
        "whatsapp_template": "Thank you for registering for {event_name}. Your registration ID is {reg_id}.",
        "qr_sharing_enabled": True,
        "exam_enabled": True,
        "is_active": True,
    },
    {
        "name": "Youth Innovation Camp",
        "slug": "youth-innovation-camp",
        "description": "Dummy demo event with a lighter data collection module for quick sign-ups.",
        "registration_type": "public",
        "collect_photo": False,
        "requires_photo": False,
        "collect_email": True,
        "collect_designation": False,
        "collect_subject": False,
        "collect_school_name": False,
        "collect_school_area": False,
        "collect_block": False,
        "marquee_message": "New: Youth Innovation Camp is now available on the public portal.",
        "payment_enabled": False,
        "payment_amount": 0,
        "payment_link": "",
        "payment_notes": "",
        "whatsapp_ack_enabled": False,
        "whatsapp_template": "",
        "qr_sharing_enabled": False,
        "exam_enabled": False,
        "is_active": True,
    },
]


DEFAULT_FIELD_OPTIONS = {
    "salutation": "\n".join(["Mr.", "Mrs.", "Ms.", "Dr."]),
    "designation": "\n".join([
        "Headmaster",
        "Headmistress",
        "PG Assistant",
        "BT Assistant",
        "Secondary Grade Teacher",
        "Vocational Instructor",
        "Physical Education Teacher",
        "Special Teacher",
        "Computer Instructor",
        "Other",
    ]),
    "subject": "\n".join([
        "Tamil",
        "English",
        "Mathematics",
        "Science",
        "Physics",
        "Chemistry",
        "Biology",
        "History",
        "Geography",
        "Economics",
        "Commerce",
        "Computer Science",
        "Physical Education",
        "Other",
    ]),
    "block": "\n".join([
        "Perambalur",
        "Alathur",
        "Veppanthattai",
        "Veppur",
        "Kunnam",
    ]),
    "gender": "\n".join([
        "Male",
        "Female",
        "Other",
    ]),
}


DEFAULT_EVENT_FIELDS = {
    "teacher": [
        {"field_name": "salutation", "field_label": "Salutation", "field_type": "select", "data_type": "string", "options_text": DEFAULT_FIELD_OPTIONS["salutation"], "is_required": True, "sort_order": 10},
        {"field_name": "teacher_name", "field_label": "Teacher Name", "field_type": "text", "data_type": "string", "placeholder": "Enter teacher name", "is_required": True, "sort_order": 20},
        {"field_name": "mobile", "field_label": "Mobile Number", "field_type": "tel", "data_type": "string", "placeholder": "9876543210", "is_required": True, "sort_order": 30},
        {"field_name": "email", "field_label": "Email Address", "field_type": "email", "data_type": "string", "placeholder": "example@gmail.com", "is_required": True, "sort_order": 40},
        {"field_name": "designation", "field_label": "Designation", "field_type": "select", "data_type": "string", "options_text": DEFAULT_FIELD_OPTIONS["designation"], "is_required": True, "sort_order": 50},
        {"field_name": "subject", "field_label": "Subject", "field_type": "select", "data_type": "string", "options_text": DEFAULT_FIELD_OPTIONS["subject"], "is_required": True, "sort_order": 60},
        {"field_name": "school_name", "field_label": "School Name", "field_type": "text", "data_type": "string", "placeholder": "Enter school name", "is_required": True, "sort_order": 70},
        {"field_name": "school_area", "field_label": "School Area", "field_type": "text", "data_type": "string", "placeholder": "Village / Town / City", "is_required": True, "sort_order": 80},
        {"field_name": "block", "field_label": "Block", "field_type": "select", "data_type": "string", "options_text": DEFAULT_FIELD_OPTIONS["block"], "is_required": True, "sort_order": 90},
    ],
    "student": [
        {"field_name": "teacher_name", "field_label": "Student Name", "field_type": "text", "data_type": "string", "placeholder": "Enter student name", "is_required": True, "sort_order": 10},
        {"field_name": "mobile", "field_label": "Mobile Number", "field_type": "tel", "data_type": "string", "placeholder": "9876543210", "is_required": True, "sort_order": 20},
        {"field_name": "email", "field_label": "Email Address", "field_type": "email", "data_type": "string", "placeholder": "example@gmail.com", "is_required": False, "sort_order": 30},
        {"field_name": "school_name", "field_label": "School / College Name", "field_type": "text", "data_type": "string", "placeholder": "Enter school or college name", "is_required": True, "sort_order": 40},
        {"field_name": "custom_grade", "field_label": "Class / Grade", "field_type": "text", "data_type": "string", "placeholder": "Enter class or grade", "is_required": True, "sort_order": 50},
        {"field_name": "custom_gender", "field_label": "Gender", "field_type": "select", "data_type": "string", "options_text": DEFAULT_FIELD_OPTIONS["gender"], "is_required": False, "sort_order": 60},
    ],
    "public": [
        {"field_name": "teacher_name", "field_label": "Participant Name", "field_type": "text", "data_type": "string", "placeholder": "Enter participant name", "is_required": True, "sort_order": 10},
        {"field_name": "mobile", "field_label": "Mobile Number", "field_type": "tel", "data_type": "string", "placeholder": "9876543210", "is_required": True, "sort_order": 20},
        {"field_name": "email", "field_label": "Email Address", "field_type": "email", "data_type": "string", "placeholder": "example@gmail.com", "is_required": False, "sort_order": 30},
        {"field_name": "custom_place", "field_label": "Place", "field_type": "text", "data_type": "string", "placeholder": "Enter your place", "is_required": False, "sort_order": 40},
    ],
}


def default_fields_for_registration_type(registration_type):
    if registration_type == "no_registration":
        return []

    return DEFAULT_EVENT_FIELDS.get(
        registration_type or "teacher",
        DEFAULT_EVENT_FIELDS["teacher"]
    )


def seed_default_events():
    existing_events = {
        event.slug: event
        for event in Event.query.all()
    }

    changed = False

    for item in DEFAULT_EVENTS:
        existing = existing_events.get(item["slug"])

        if not existing:
            db.session.add(Event(**item))
            changed = True
            continue

        for key, value in item.items():
            if getattr(existing, key, None) is None:
                setattr(existing, key, value)
                changed = True

    if changed:
        db.session.commit()


def seed_default_event_fields():
    changed = False

    for event in Event.query.all():
        if event.registration_fields:
            continue

        for item in default_fields_for_registration_type(event.registration_type):
            db.session.add(
                EventField(
                    event_id=event.id,
                    field_name=item["field_name"],
                    field_label=item["field_label"],
                    field_type=item.get("field_type", "text"),
                    data_type=item.get("data_type", "string"),
                    placeholder=item.get("placeholder", ""),
                    options_text=item.get("options_text", ""),
                    help_text=item.get("help_text", ""),
                    is_required=bool(item.get("is_required", False)),
                    is_active=True,
                    sort_order=item.get("sort_order", 0),
                )
            )
            changed = True

    if changed:
        db.session.commit()


def init_database():
    try:
        with app.app_context():
            seed_default_events()
            seed_default_event_fields()
            seed_default_blocks()
    except Exception as e:
        print("WARNING: database initialization failed:", e)


def seed_default_blocks():
    if Block.query.count() > 0:
        return

    blocks = [
        Block(block_name="Perambalur", certificate_template="winner.png"),
        Block(block_name="Veppanthattai", certificate_template="winner.png"),
        Block(block_name="Alathur", certificate_template="winner.png"),
        Block(block_name="Kunnam", certificate_template="winner.png"),
        Block(block_name="Veppur", certificate_template="winner.png"),
    ]

    db.session.add_all(blocks)
    db.session.commit()


@app.cli.command("seed-data")
def seed_data_command():
    init_database()
    print("Default events, fields, and blocks seeded.")


# ==========================
# Run Application
# ==========================

if __name__ == "__main__":
    init_database()
    app.run(debug=True)
