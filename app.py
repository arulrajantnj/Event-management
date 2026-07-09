from flask import Flask
import os
import sqlite3

from models import db, Event, EventField, ExamAnswer, ExamAttempt, ExamQuestion, ExamSubject, OnlineExam

from routes import routes as routes_bp
from admin_routes import admin_bp
from attendance_routes import attendance_bp
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
db_path = os.path.abspath(os.path.join(app.instance_path, "event.db"))
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + db_path.replace('\\', '/')
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# ==========================
# Upload Folder
# ==========================

app.config["UPLOAD_FOLDER"] = "static/certificate_templates"

os.makedirs("static/certificate_templates", exist_ok=True)
# Generated Files
os.makedirs("static/generated_certificates", exist_ok=True)
os.makedirs("static/generated_qr", exist_ok=True)
os.makedirs("static/uploads", exist_ok=True)
os.makedirs("static/sponsors", exist_ok=True)
os.makedirs("qrcodes", exist_ok=True)

# ==========================
# Initialize Database
# ==========================

db.init_app(app)


# ==========================
# Register Blueprints
# ==========================

app.register_blueprint(routes_bp)
app.register_blueprint(attendance_bp)
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
        "whatsapp_group_enabled": False,
        "whatsapp_group_link": "",
        "acknowledgement_enabled": True,
        "certificate_enabled": True,
        "attendance_enabled": False,
        "code_type": "qr",
        "code_fields": "attendance_url\nreg_id\nparticipant_name\nevent_name",
        "reg_id_prefix": "TCH",
        "reg_id_next_number": 1,
        "reg_id_padding": 4,
        "sponsor_brand": "",
        "sponsor_logo": "",
        "sponsor_image": "",
        "sponsor_logo_position": "left",
        "sponsor_logo_width": 160,
        "sponsor_logo_height": 90,
        "sponsor_banner_position": "right",
        "sponsor_banner_width": 520,
        "sponsor_banner_height": 170,
        "sponsor_image_fit": "contain",
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
        "whatsapp_group_enabled": False,
        "whatsapp_group_link": "",
        "acknowledgement_enabled": True,
        "certificate_enabled": True,
        "attendance_enabled": False,
        "code_type": "qr",
        "code_fields": "attendance_url\nreg_id\nparticipant_name\nevent_name",
        "reg_id_prefix": "SLW",
        "reg_id_next_number": 1,
        "reg_id_padding": 4,
        "sponsor_brand": "",
        "sponsor_logo": "",
        "sponsor_image": "",
        "sponsor_logo_position": "left",
        "sponsor_logo_width": 160,
        "sponsor_logo_height": 90,
        "sponsor_banner_position": "right",
        "sponsor_banner_width": 520,
        "sponsor_banner_height": 170,
        "sponsor_image_fit": "contain",
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
        "whatsapp_group_enabled": False,
        "whatsapp_group_link": "",
        "acknowledgement_enabled": True,
        "certificate_enabled": True,
        "attendance_enabled": False,
        "code_type": "qr",
        "code_fields": "attendance_url\nreg_id\nparticipant_name\nevent_name",
        "reg_id_prefix": "YIC",
        "reg_id_next_number": 1,
        "reg_id_padding": 4,
        "sponsor_brand": "",
        "sponsor_logo": "",
        "sponsor_image": "",
        "sponsor_logo_position": "left",
        "sponsor_logo_width": 160,
        "sponsor_logo_height": 90,
        "sponsor_banner_position": "right",
        "sponsor_banner_width": 520,
        "sponsor_banner_height": 170,
        "sponsor_image_fit": "contain",
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


def ensure_event_schema():
    db_path = os.path.join(app.instance_path, "event.db")

    if not os.path.exists(db_path):
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(events)")
    existing_columns = {row[1] for row in cursor.fetchall()}

    required_columns = {
        "registration_type": "registration_type VARCHAR(30) DEFAULT 'teacher'",
        "collect_photo": "collect_photo BOOLEAN DEFAULT 1",
        "collect_email": "collect_email BOOLEAN DEFAULT 1",
        "collect_designation": "collect_designation BOOLEAN DEFAULT 1",
        "collect_subject": "collect_subject BOOLEAN DEFAULT 1",
        "collect_school_name": "collect_school_name BOOLEAN DEFAULT 1",
        "collect_school_area": "collect_school_area BOOLEAN DEFAULT 1",
        "collect_block": "collect_block BOOLEAN DEFAULT 1",
        "marquee_message": "marquee_message VARCHAR(255)",
        "payment_enabled": "payment_enabled BOOLEAN DEFAULT 0",
        "payment_amount": "payment_amount FLOAT DEFAULT 0",
        "payment_link": "payment_link VARCHAR(500)",
        "payment_notes": "payment_notes TEXT",
        "whatsapp_ack_enabled": "whatsapp_ack_enabled BOOLEAN DEFAULT 0",
        "whatsapp_template": "whatsapp_template TEXT",
        "whatsapp_group_enabled": "whatsapp_group_enabled BOOLEAN DEFAULT 0",
        "whatsapp_group_link": "whatsapp_group_link VARCHAR(500)",
        "acknowledgement_enabled": "acknowledgement_enabled BOOLEAN DEFAULT 1",
        "certificate_enabled": "certificate_enabled BOOLEAN DEFAULT 1",
        "attendance_enabled": "attendance_enabled BOOLEAN DEFAULT 0",
        "code_type": "code_type VARCHAR(20) DEFAULT 'qr'",
        "code_fields": "code_fields TEXT",
        "reg_id_prefix": "reg_id_prefix VARCHAR(20) DEFAULT 'EVT'",
        "reg_id_next_number": "reg_id_next_number INTEGER DEFAULT 1",
        "reg_id_padding": "reg_id_padding INTEGER DEFAULT 4",
        "sponsor_brand": "sponsor_brand VARCHAR(150)",
        "sponsor_logo": "sponsor_logo VARCHAR(250)",
        "sponsor_image": "sponsor_image VARCHAR(250)",
        "sponsor_logo_position": "sponsor_logo_position VARCHAR(20) DEFAULT 'left'",
        "sponsor_logo_width": "sponsor_logo_width INTEGER DEFAULT 160",
        "sponsor_logo_height": "sponsor_logo_height INTEGER DEFAULT 90",
        "sponsor_banner_position": "sponsor_banner_position VARCHAR(20) DEFAULT 'right'",
        "sponsor_banner_width": "sponsor_banner_width INTEGER DEFAULT 520",
        "sponsor_banner_height": "sponsor_banner_height INTEGER DEFAULT 170",
        "sponsor_image_fit": "sponsor_image_fit VARCHAR(20) DEFAULT 'contain'",
        "qr_sharing_enabled": "qr_sharing_enabled BOOLEAN DEFAULT 1",
        "exam_enabled": "exam_enabled BOOLEAN DEFAULT 0",
    }

    for name, ddl in required_columns.items():
        if name not in existing_columns:
            cursor.execute(f"ALTER TABLE events ADD COLUMN {ddl}")

    conn.commit()
    conn.close()


def ensure_exam_schema():
    db_path = os.path.join(app.instance_path, "event.db")

    if not os.path.exists(db_path):
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    table_columns = {}
    for table_name in ("online_exams", "exam_questions", "exam_attempts"):
        cursor.execute(f"PRAGMA table_info({table_name})")
        table_columns[table_name] = {row[1] for row in cursor.fetchall()}

    online_exam_columns = {
        "start_at": "start_at DATETIME",
        "end_at": "end_at DATETIME",
        "negative_marks": "negative_marks FLOAT DEFAULT 0",
        "tab_switch_limit": "tab_switch_limit INTEGER DEFAULT 3",
        "auto_submit_on_violation": "auto_submit_on_violation BOOLEAN DEFAULT 1",
    }

    for name, ddl in online_exam_columns.items():
        if name not in table_columns.get("online_exams", set()):
            cursor.execute(f"ALTER TABLE online_exams ADD COLUMN {ddl}")

    question_columns = {
        "question_type": "question_type VARCHAR(20) DEFAULT 'mcq'",
        "model_answer": "model_answer TEXT",
    }

    for name, ddl in question_columns.items():
        if name not in table_columns.get("exam_questions", set()):
            cursor.execute(f"ALTER TABLE exam_questions ADD COLUMN {ddl}")

    attempt_columns = {
        "started_at": "started_at DATETIME",
        "evaluation_status": "evaluation_status VARCHAR(30) DEFAULT 'auto_scored'",
        "violation_count": "violation_count INTEGER DEFAULT 0",
    }

    for name, ddl in attempt_columns.items():
        if name not in table_columns.get("exam_attempts", set()):
            cursor.execute(f"ALTER TABLE exam_attempts ADD COLUMN {ddl}")

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='exam_answers'")
    if not cursor.fetchone():
        cursor.execute(
            """
            CREATE TABLE exam_answers (
                id INTEGER NOT NULL PRIMARY KEY,
                attempt_id INTEGER NOT NULL,
                question_id INTEGER NOT NULL,
                selected_option VARCHAR(1),
                text_answer TEXT,
                is_correct BOOLEAN,
                auto_score FLOAT DEFAULT 0 NOT NULL,
                manual_score FLOAT,
                created_at DATETIME,
                FOREIGN KEY(attempt_id) REFERENCES exam_attempts (id),
                FOREIGN KEY(question_id) REFERENCES exam_questions (id)
            )
            """
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_exam_answers_attempt_id "
            "ON exam_answers (attempt_id)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_exam_answers_question_id "
            "ON exam_answers (question_id)"
        )

    conn.commit()
    conn.close()


def ensure_participant_schema():
    db_path = os.path.join(app.instance_path, "event.db")

    if not os.path.exists(db_path):
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(participants)")
    existing_columns = {row[1] for row in cursor.fetchall()}

    cursor.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='participants'"
    )
    row = cursor.fetchone()
    table_sql = row[0] if row and row[0] else ""

    needs_rebuild = (
        "event_id" not in existing_columns
        or "UNIQUE (mobile)" in table_sql
        or "photo_with_mp" in existing_columns
        or "ai_status" in existing_columns
        or "ai_photo" in existing_columns
        or "ai_generated" in existing_columns
    )

    if needs_rebuild:
        cursor.execute(
            "SELECT id FROM events WHERE is_active = 1 ORDER BY id LIMIT 1"
        )
        event_row = cursor.fetchone()
        if not event_row:
            cursor.execute(
                "SELECT id FROM events ORDER BY id LIMIT 1"
            )
            event_row = cursor.fetchone()

        default_event_id = event_row[0] if event_row else 1
        event_expr = (
            f"COALESCE(event_id, {default_event_id})"
            if "event_id" in existing_columns
            else str(default_event_id)
        )
        extra_data_expr = (
            "extra_data"
            if "extra_data" in existing_columns
            else "NULL"
        )
        exam_username_expr = (
            "exam_username"
            if "exam_username" in existing_columns
            else "NULL"
        )
        exam_password_hash_expr = (
            "exam_password_hash"
            if "exam_password_hash" in existing_columns
            else "NULL"
        )

        cursor.execute("PRAGMA foreign_keys = OFF")
        cursor.execute(
            """
            CREATE TABLE participants_new (
                id INTEGER NOT NULL PRIMARY KEY,
                reg_id VARCHAR(30) NOT NULL UNIQUE,
                event_id INTEGER NOT NULL,
                salutation VARCHAR(20),
                teacher_name VARCHAR(150) NOT NULL,
                mobile VARCHAR(10) NOT NULL,
                email VARCHAR(120) NOT NULL,
                designation VARCHAR(100) NOT NULL,
                subject VARCHAR(100) NOT NULL,
                school_name VARCHAR(200) NOT NULL,
                school_area VARCHAR(150) NOT NULL,
                block VARCHAR(100) NOT NULL,
                photo VARCHAR(250),
                extra_data TEXT,
                certificate_pdf VARCHAR(250),
                qr_code VARCHAR(250),
                download_count INTEGER DEFAULT 0,
                is_present BOOLEAN DEFAULT 0,
                attendance_marked_at DATETIME,
                last_download DATETIME,
                certificate_generated BOOLEAN DEFAULT 0,
                exam_username VARCHAR(80),
                exam_password_hash VARCHAR(255),
                created_at DATETIME,
                FOREIGN KEY(event_id) REFERENCES events (id)
            )
            """
        )
        cursor.execute(
            f"""
            INSERT INTO participants_new (
                id,
                reg_id,
                event_id,
                salutation,
                teacher_name,
                mobile,
                email,
                designation,
                subject,
                school_name,
                school_area,
                block,
                photo,
                extra_data,
                certificate_pdf,
                qr_code,
                download_count,
                is_present,
                attendance_marked_at,
                last_download,
                certificate_generated,
                exam_username,
                exam_password_hash,
                created_at
            )
            SELECT
                id,
                reg_id,
                {event_expr},
                salutation,
                teacher_name,
                mobile,
                email,
                designation,
                subject,
                school_name,
                school_area,
                block,
                photo,
                {extra_data_expr},
                certificate_pdf,
                qr_code,
                COALESCE(download_count, 0),
                0,
                NULL,
                last_download,
                COALESCE(certificate_generated, 0),
                {exam_username_expr},
                {exam_password_hash_expr},
                created_at
            FROM participants
            """
        )
        cursor.execute("DROP TABLE participants")
        cursor.execute("ALTER TABLE participants_new RENAME TO participants")
        cursor.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_participants_reg_id_unique "
            "ON participants (reg_id)"
        )
        cursor.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_participants_event_mobile_unique "
            "ON participants (event_id, mobile)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_participants_event_id "
            "ON participants (event_id)"
        )
        cursor.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_participants_exam_username_unique "
            "ON participants (exam_username)"
        )
        cursor.execute("PRAGMA foreign_keys = ON")
    else:
        required_columns = {
            "event_id": "event_id INTEGER",
            "extra_data": "extra_data TEXT",
            "certificate_pdf": "certificate_pdf VARCHAR(250)",
            "qr_code": "qr_code VARCHAR(250)",
            "download_count": "download_count INTEGER DEFAULT 0",
            "is_present": "is_present BOOLEAN DEFAULT 0",
            "attendance_marked_at": "attendance_marked_at DATETIME",
            "last_download": "last_download DATETIME",
            "certificate_generated": "certificate_generated BOOLEAN DEFAULT 0",
            "exam_username": "exam_username VARCHAR(80)",
            "exam_password_hash": "exam_password_hash VARCHAR(255)",
        }

        for name, ddl in required_columns.items():
            if name not in existing_columns:
                cursor.execute(f"ALTER TABLE participants ADD COLUMN {ddl}")

        cursor.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_participants_reg_id_unique "
            "ON participants (reg_id)"
        )
        cursor.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_participants_event_mobile_unique "
            "ON participants (event_id, mobile)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_participants_event_id "
            "ON participants (event_id)"
        )
        cursor.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_participants_exam_username_unique "
            "ON participants (exam_username)"
        )

    conn.commit()
    conn.close()


def init_database():
    try:
        with app.app_context():
            db.create_all()
            ensure_event_schema()
            ensure_exam_schema()
            seed_default_events()
            ensure_participant_schema()
            seed_default_event_fields()
    except Exception as e:
        print("WARNING: database initialization failed:", e)

# Attempt to initialize the database, but do not stop app import on failure.
init_database()
from models import Block

with app.app_context():

    if Block.query.count() == 0:

        blocks = [

            Block(
                block_name="Perambalur",
                certificate_template="winner.png"
            ),

            Block(
                block_name="Veppanthattai",
                certificate_template="winner.png"
            ),

            Block(
                block_name="Alathur",
                certificate_template="winner.png"
            ),

            Block(
                block_name="Kunnam",
                certificate_template="winner.png"
            ),

            Block(
                block_name="Veppur",
                certificate_template="winner.png"
            )

        ]

        db.session.add_all(blocks)

        db.session.commit()
# ==========================
# Run Application
# ==========================

if __name__ == "__main__":
    init_database()
    app.run(debug=True)
