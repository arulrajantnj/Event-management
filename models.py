from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()

# ==========================================================
# EVENT
# ==========================================================
class Event(db.Model):

    __tablename__ = "events"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(150),
        nullable=False
    )

    slug = db.Column(
        db.String(160),
        unique=True,
        nullable=False
    )

    description = db.Column(
        db.Text
    )

    registration_type = db.Column(
        db.String(30),
        default="teacher",
        nullable=False
    )

    # Public registrations and spreadsheet imports can be enabled independently.
    public_registration_enabled = db.Column(
        db.Boolean,
        default=True,
        nullable=False
    )

    participant_bulk_upload_enabled = db.Column(
        db.Boolean,
        default=False,
        nullable=False
    )

    show_venue = db.Column(db.Boolean, default=False, nullable=False)
    venue = db.Column(db.String(255))
    show_event_date = db.Column(db.Boolean, default=False, nullable=False)
    event_date = db.Column(db.Date)
    show_event_time = db.Column(db.Boolean, default=False, nullable=False)
    event_time = db.Column(db.String(100))
    show_chief_guest = db.Column(db.Boolean, default=False, nullable=False)
    chief_guest = db.Column(db.String(255))

    requires_photo = db.Column(
        db.Boolean,
        default=True,
        nullable=False
    )

    collect_photo = db.Column(
        db.Boolean,
        default=True,
        nullable=False
    )

    collect_email = db.Column(
        db.Boolean,
        default=True,
        nullable=False
    )

    collect_designation = db.Column(
        db.Boolean,
        default=True,
        nullable=False
    )

    collect_subject = db.Column(
        db.Boolean,
        default=True,
        nullable=False
    )

    collect_school_name = db.Column(
        db.Boolean,
        default=True,
        nullable=False
    )

    collect_school_area = db.Column(
        db.Boolean,
        default=True,
        nullable=False
    )

    collect_block = db.Column(
        db.Boolean,
        default=True,
        nullable=False
    )

    marquee_message = db.Column(
        db.String(255)
    )
    title_font_family = db.Column(db.String(120), default="Poppins", nullable=False)
    description_font_family = db.Column(db.String(120), default="Poppins", nullable=False)
    marquee_font_family = db.Column(db.String(120), default="Poppins", nullable=False)
    registration_font_family = db.Column(db.String(120), default="Poppins", nullable=False)
    title_font_color = db.Column(db.String(7), default="#ffffff", nullable=False)
    title_font_size = db.Column(db.Integer, default=0, nullable=False)
    description_font_color = db.Column(db.String(7), default="#6c757d", nullable=False)
    description_font_size = db.Column(db.Integer, default=0, nullable=False)
    marquee_font_color = db.Column(db.String(7), default="#ffffff", nullable=False)
    marquee_font_size = db.Column(db.Integer, default=0, nullable=False)
    registration_font_color = db.Column(db.String(7), default="#0d6efd", nullable=False)
    registration_font_size = db.Column(db.Integer, default=0, nullable=False)

    # Optional content shown above the participant registration form.
    registration_header = db.Column(db.String(255))
    registration_instructions = db.Column(db.Text)
    show_registration_header = db.Column(db.Boolean, default=True, nullable=False)
    show_registration_instructions = db.Column(db.Boolean, default=True, nullable=False)
    show_registration_sponsor = db.Column(db.Boolean, default=False, nullable=False)

    payment_enabled = db.Column(
        db.Boolean,
        default=False,
        nullable=False
    )

    payment_amount = db.Column(
        db.Float,
        default=0
    )

    payment_link = db.Column(
        db.String(500)
    )

    payment_notes = db.Column(
        db.Text
    )

    payment_gateway = db.Column(db.String(30), default="manual", nullable=False)

    whatsapp_ack_enabled = db.Column(
        db.Boolean,
        default=False,
        nullable=False
    )

    whatsapp_template = db.Column(
        db.Text
    )

    # One field key per line. These optional details are appended to a
    # WhatsApp acknowledgement after its custom template.
    whatsapp_ack_fields = db.Column(db.Text)

    whatsapp_group_enabled = db.Column(
        db.Boolean,
        default=False,
        nullable=False
    )

    whatsapp_group_link = db.Column(
        db.String(500)
    )

    acknowledgement_enabled = db.Column(
        db.Boolean,
        default=True,
        nullable=False
    )

    acknowledgement_instructions = db.Column(db.Text)
    show_acknowledgement_instructions = db.Column(db.Boolean, default=False, nullable=False)
    acknowledgement_thank_you = db.Column(db.String(500))
    show_acknowledgement_thank_you = db.Column(db.Boolean, default=False, nullable=False)
    show_acknowledgement_payment_details = db.Column(db.Boolean, default=False, nullable=False)

    certificate_enabled = db.Column(
        db.Boolean,
        default=True,
        nullable=False
    )

    attendance_enabled = db.Column(
        db.Boolean,
        default=False,
        nullable=False
    )

    code_type = db.Column(
        db.String(20),
        default="qr",
        nullable=False
    )

    code_fields = db.Column(
        db.Text
    )

    reg_id_prefix = db.Column(
        db.String(20),
        default="EVT"
    )

    reg_id_next_number = db.Column(
        db.Integer,
        default=1,
        nullable=False
    )

    reg_id_padding = db.Column(
        db.Integer,
        default=4,
        nullable=False
    )

    sponsor_brand = db.Column(
        db.String(150)
    )

    sponsor_logo = db.Column(
        db.String(250)
    )

    sponsor_image = db.Column(
        db.String(250)
    )

    sponsor_logo_position = db.Column(
        db.String(20),
        default="left"
    )

    sponsor_logo_width = db.Column(
        db.Integer,
        default=160
    )

    sponsor_logo_height = db.Column(
        db.Integer,
        default=90
    )

    sponsor_banner_position = db.Column(
        db.String(20),
        default="right"
    )

    sponsor_banner_width = db.Column(
        db.Integer,
        default=520
    )

    sponsor_banner_height = db.Column(
        db.Integer,
        default=170
    )

    sponsor_image_fit = db.Column(
        db.String(20),
        default="contain"
    )

    hero_priority = db.Column(
        db.Integer,
        default=0,
        nullable=False
    )

    qr_sharing_enabled = db.Column(
        db.Boolean,
        default=True,
        nullable=False
    )

    exam_enabled = db.Column(
        db.Boolean,
        default=False,
        nullable=False
    )

    is_active = db.Column(
        db.Boolean,
        default=True,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    participants = db.relationship(
        "Participant",
        back_populates="event",
        lazy=True
    )

    attendance_records = db.relationship(
        "Attendance",
        back_populates="event",
        cascade="all, delete-orphan",
        lazy=True
    )

    attendance_logs = db.relationship(
        "AttendanceLog",
        back_populates="event",
        cascade="all, delete-orphan",
        lazy=True
    )

    registration_fields = db.relationship(
        "EventField",
        back_populates="event",
        cascade="all, delete-orphan",
        order_by="EventField.sort_order.asc(), EventField.id.asc()",
        lazy=True
    )

    exam_subjects = db.relationship(
        "ExamSubject",
        back_populates="event",
        cascade="all, delete-orphan",
        order_by="ExamSubject.subject_name.asc()",
        lazy=True
    )

    online_exams = db.relationship(
        "OnlineExam",
        back_populates="event",
        cascade="all, delete-orphan",
        order_by="OnlineExam.created_at.desc()",
        lazy=True
    )


# Homepage posters, notices and calls-to-action managed from the admin panel.
class HomepagePromotion(db.Model):

    __tablename__ = "homepage_promotions"

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(180), nullable=False)
    message = db.Column(db.Text)
    image_filename = db.Column(db.String(250))
    link_url = db.Column(db.String(500))
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    show_before_priority = db.Column(db.Boolean, default=True, nullable=False)
    sort_order = db.Column(db.Integer, default=0, nullable=False)
    layout = db.Column(db.String(20), default="banner", nullable=False)
    image_fit = db.Column(db.String(20), default="cover", nullable=False)
    accent_color = db.Column(db.String(20), default="#0d6efd", nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


# ==========================================================
# PARTICIPANT
# ==========================================================
class Participant(db.Model):

    __tablename__ = "participants"
    __table_args__ = (
        db.UniqueConstraint(
            "event_id",
            "mobile",
            name="uq_participants_event_mobile"
        ),
    )

    id = db.Column(db.Integer, primary_key=True)

    reg_id = db.Column(db.String(30), unique=True, nullable=False)

    event_id = db.Column(
        db.Integer,
        db.ForeignKey("events.id"),
        nullable=False
    )

    salutation = db.Column(db.String(20))

    teacher_name = db.Column(db.String(150), nullable=False)

    mobile = db.Column(db.String(10), nullable=False)

    email = db.Column(db.String(120), nullable=False)

    designation = db.Column(db.String(100), nullable=False)

    subject = db.Column(db.String(100), nullable=False)

    school_name = db.Column(db.String(200), nullable=False)

    school_area = db.Column(db.String(150), nullable=False)

    block = db.Column(db.String(100), nullable=False)

    photo = db.Column(db.String(250))

    extra_data = db.Column(
        db.Text
    )

    payment_status = db.Column(db.String(30), default="not_required", nullable=False)
    razorpay_order_id = db.Column(db.String(100), unique=True)
    razorpay_payment_id = db.Column(db.String(100), unique=True)
    payment_verified_at = db.Column(db.DateTime)

    # ----------------------------
    # DOWNLOAD FILES
    # ----------------------------

    certificate_pdf = db.Column(
        db.String(250)
    )

    qr_code = db.Column(
        db.String(250)
    )

    download_count = db.Column(
        db.Integer,
        default=0
    )

    is_present = db.Column(
        db.Boolean,
        default=False,
        nullable=False
    )

    attendance_marked_at = db.Column(
        db.DateTime
    )

    last_download = db.Column(
        db.DateTime
    )

    certificate_generated = db.Column(
        db.Boolean,
        default=False
    )

    certificate_approved = db.Column(
        db.Boolean,
        default=False,
        nullable=False
    )

    certificate_approved_at = db.Column(db.DateTime)

    # ----------------------------
    # EXAM LOGIN
    # ----------------------------

    exam_username = db.Column(
        db.String(80),
        unique=True
    )

    exam_password_hash = db.Column(
        db.String(255)
    )

    # ----------------------------
    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    event = db.relationship(
        "Event",
        back_populates="participants"
    )

    attendance_records = db.relationship(
        "Attendance",
        back_populates="participant",
        cascade="all, delete-orphan",
        lazy=True
    )

    attendance_logs = db.relationship(
        "AttendanceLog",
        back_populates="participant",
        cascade="all, delete-orphan",
        lazy=True
    )

    exam_attempts = db.relationship(
        "ExamAttempt",
        back_populates="participant",
        cascade="all, delete-orphan",
        lazy=True
    )

    def extra_data_map(self):
        if not self.extra_data:
            return {}

        try:
            data = json.loads(self.extra_data)
        except (TypeError, ValueError):
            return {}

        return data if isinstance(data, dict) else {}

    def extra_data_items(self):
        items = []

        for field_name, item in self.extra_data_map().items():
            if isinstance(item, dict):
                label = item.get("label") or field_name.replace("_", " ").title()
                value = item.get("value", "")
            else:
                label = field_name.replace("_", " ").title()
                value = item

            if value not in (None, ""):
                items.append({
                    "field_name": field_name,
                    "label": label,
                    "value": value
                })

        return items


# ==========================================================
# ATTENDANCE
# ==========================================================
class Attendance(db.Model):

    __tablename__ = "attendance"
    __table_args__ = (
        db.UniqueConstraint(
            "participant_id",
            "attendance_date",
            name="uq_attendance_participant_date"
        ),
        db.Index("idx_attendance_event_date", "event_id", "attendance_date"),
    )

    id = db.Column(db.Integer, primary_key=True)

    participant_id = db.Column(
        db.Integer,
        db.ForeignKey("participants.id"),
        nullable=False
    )

    event_id = db.Column(
        db.Integer,
        db.ForeignKey("events.id"),
        nullable=False
    )

    attendance_date = db.Column(db.Date, nullable=False)

    attendance_time = db.Column(db.DateTime, nullable=False)

    status = db.Column(db.String(30), default="Present", nullable=False)

    method = db.Column(db.String(20), default="QR", nullable=False)

    remarks = db.Column(db.Text)

    marked_by = db.Column(db.String(80))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    participant = db.relationship(
        "Participant",
        back_populates="attendance_records"
    )

    event = db.relationship(
        "Event",
        back_populates="attendance_records"
    )


class AttendanceLog(db.Model):

    __tablename__ = "attendance_logs"
    __table_args__ = (
        db.Index("idx_attendance_logs_event_created", "event_id", "created_at"),
    )

    id = db.Column(db.Integer, primary_key=True)

    participant_id = db.Column(
        db.Integer,
        db.ForeignKey("participants.id")
    )

    event_id = db.Column(
        db.Integer,
        db.ForeignKey("events.id")
    )

    action = db.Column(db.String(40), nullable=False)

    status = db.Column(db.String(30))

    method = db.Column(db.String(20))

    scan_text = db.Column(db.Text)

    message = db.Column(db.String(255))

    admin_user = db.Column(db.String(80))

    ip_address = db.Column(db.String(45))

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    participant = db.relationship(
        "Participant",
        back_populates="attendance_logs"
    )

    event = db.relationship(
        "Event",
        back_populates="attendance_logs"
    )


class ScannerUser(db.Model):

    __tablename__ = "scanner_users"
    __table_args__ = (
        db.UniqueConstraint("username", name="uq_scanner_users_username"),
    )

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(120), nullable=False)

    username = db.Column(db.String(80), nullable=False)

    password_hash = db.Column(db.String(255), nullable=False)

    event_id = db.Column(
        db.Integer,
        db.ForeignKey("events.id")
    )

    is_approved = db.Column(db.Boolean, default=False, nullable=False)

    is_active = db.Column(db.Boolean, default=True, nullable=False)

    approved_by = db.Column(db.String(80))

    approved_at = db.Column(db.DateTime)

    last_login_at = db.Column(db.DateTime)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    event = db.relationship("Event")


# ==========================================================
# EXAM DUTY ALLOCATION
# ==========================================================
class ExamDutyTeacher(db.Model):
    __tablename__ = "exam_duty_teachers"
    __table_args__ = (
        db.UniqueConstraint("event_id", "teacher_id", name="uq_exam_duty_teacher_event_id"),
    )

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey("events.id"), nullable=False)
    teacher_id = db.Column(db.String(80), nullable=False)
    teacher_name = db.Column(db.String(150), nullable=False)
    mobile = db.Column(db.String(20))
    designation = db.Column(db.String(120))
    working_school = db.Column(db.String(220))
    udise_code = db.Column(db.String(30))
    working_block = db.Column(db.String(120))
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    event = db.relationship("Event")
    allocations = db.relationship("ExamDutyAllocation", back_populates="teacher", cascade="all, delete-orphan")


class ExamDutyCenter(db.Model):
    __tablename__ = "exam_duty_centers"
    __table_args__ = (
        db.UniqueConstraint("event_id", "center_no", name="uq_exam_duty_center_number"),
    )

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey("events.id"), nullable=False)
    center_name = db.Column(db.String(220), nullable=False)
    center_no = db.Column(db.String(80), nullable=False)
    center_block = db.Column(db.String(120), nullable=False)
    invigilators_required = db.Column(db.Integer, nullable=False, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    event = db.relationship("Event")
    allocations = db.relationship("ExamDutyAllocation", back_populates="center", cascade="all, delete-orphan")


class ExamDutyAllocation(db.Model):
    __tablename__ = "exam_duty_allocations"
    __table_args__ = (
        db.UniqueConstraint("event_id", "teacher_id", name="uq_exam_duty_teacher_allocation"),
    )

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey("events.id"), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey("exam_duty_teachers.id"), nullable=False)
    center_id = db.Column(db.Integer, db.ForeignKey("exam_duty_centers.id"), nullable=False)
    allocation_method = db.Column(db.String(20), nullable=False, default="manual")
    status = db.Column(db.String(20), nullable=False, default="draft")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    event = db.relationship("Event")
    teacher = db.relationship("ExamDutyTeacher", back_populates="allocations")
    center = db.relationship("ExamDutyCenter", back_populates="allocations")


# ==========================================================
# CHILDREN'S COMPETITIONS
# ==========================================================
class Competition(db.Model):
    __tablename__ = "competitions"

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey("events.id"), nullable=False)
    name = db.Column(db.String(180), nullable=False)
    category = db.Column(db.String(100))
    description = db.Column(db.Text)
    registration_enabled = db.Column(db.Boolean, default=True, nullable=False)
    results_published = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    event = db.relationship("Event")
    registrations = db.relationship("CompetitionRegistration", back_populates="competition", cascade="all, delete-orphan")
    judges = db.relationship("CompetitionJudge", back_populates="competition", cascade="all, delete-orphan")


class CompetitionRegistration(db.Model):
    __tablename__ = "competition_registrations"
    __table_args__ = (db.UniqueConstraint("competition_id", "mobile", "participant_name", name="uq_competition_registration"),)

    id = db.Column(db.Integer, primary_key=True)
    competition_id = db.Column(db.Integer, db.ForeignKey("competitions.id"), nullable=False)
    registration_no = db.Column(db.String(32), unique=True, nullable=False)
    participant_name = db.Column(db.String(150), nullable=False)
    gender = db.Column(db.String(20), nullable=False, default="Not specified")
    age = db.Column(db.Integer)
    mobile = db.Column(db.String(20))
    school_name = db.Column(db.String(220))
    class_name = db.Column(db.String(60))
    is_present = db.Column(db.Boolean, default=False, nullable=False)
    score = db.Column(db.Float)
    rank = db.Column(db.String(40), default="Participant Certificate", nullable=False)
    judge_submitted_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    competition = db.relationship("Competition", back_populates="registrations")


class CompetitionJudge(db.Model):
    __tablename__ = "competition_judges"
    __table_args__ = (db.UniqueConstraint("username", name="uq_competition_judge_username"),)

    id = db.Column(db.Integer, primary_key=True)
    competition_id = db.Column(db.Integer, db.ForeignKey("competitions.id"), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    username = db.Column(db.String(80), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    competition = db.relationship("Competition", back_populates="judges")


# ==========================================================
# EVENT REGISTRATION FIELDS
# ==========================================================
class EventField(db.Model):

    __tablename__ = "event_fields"
    __table_args__ = (
        db.UniqueConstraint(
            "event_id",
            "field_name",
            name="uq_event_field_name_per_event"
        ),
    )

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    event_id = db.Column(
        db.Integer,
        db.ForeignKey("events.id"),
        nullable=False
    )

    field_name = db.Column(
        db.String(100),
        nullable=False
    )

    field_label = db.Column(
        db.String(150),
        nullable=False
    )

    field_type = db.Column(
        db.String(30),
        default="text",
        nullable=False
    )

    data_type = db.Column(
        db.String(30),
        default="string",
        nullable=False
    )

    placeholder = db.Column(
        db.String(255)
    )

    options_text = db.Column(
        db.Text
    )

    help_text = db.Column(
        db.String(255)
    )

    is_required = db.Column(
        db.Boolean,
        default=False,
        nullable=False
    )

    is_active = db.Column(
        db.Boolean,
        default=True,
        nullable=False
    )

    sort_order = db.Column(
        db.Integer,
        default=0,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    event = db.relationship(
        "Event",
        back_populates="registration_fields"
    )

    def options_list(self):
        if not self.options_text:
            return []

        return [
            option.strip()
            for option in self.options_text.splitlines()
            if option.strip()
        ]


# ==========================================================
# EXAM SUBJECTS
# ==========================================================
class ExamSubject(db.Model):

    __tablename__ = "exam_subjects"
    __table_args__ = (
        db.UniqueConstraint(
            "event_id",
            "subject_name",
            name="uq_exam_subject_per_event"
        ),
    )

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    event_id = db.Column(
        db.Integer,
        db.ForeignKey("events.id"),
        nullable=False
    )

    subject_name = db.Column(
        db.String(150),
        nullable=False
    )

    description = db.Column(
        db.Text
    )

    is_active = db.Column(
        db.Boolean,
        default=True,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    event = db.relationship(
        "Event",
        back_populates="exam_subjects"
    )

    exams = db.relationship(
        "OnlineExam",
        back_populates="subject",
        lazy=True
    )


# ==========================================================
# ONLINE EXAMS
# ==========================================================
class OnlineExam(db.Model):

    __tablename__ = "online_exams"
    __table_args__ = (
        db.UniqueConstraint(
            "exam_code",
            name="uq_online_exam_code"
        ),
    )

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    event_id = db.Column(
        db.Integer,
        db.ForeignKey("events.id"),
        nullable=False
    )

    subject_id = db.Column(
        db.Integer,
        db.ForeignKey("exam_subjects.id"),
        nullable=False
    )

    exam_title = db.Column(
        db.String(200),
        nullable=False
    )

    exam_code = db.Column(
        db.String(80),
        nullable=False
    )

    instructions = db.Column(
        db.Text
    )

    start_at = db.Column(
        db.DateTime
    )

    end_at = db.Column(
        db.DateTime
    )

    duration_minutes = db.Column(
        db.Integer,
        default=30,
        nullable=False
    )

    marks_per_question = db.Column(
        db.Float,
        default=1,
        nullable=False
    )

    pass_mark = db.Column(
        db.Float,
        default=0
    )

    negative_marks = db.Column(
        db.Float,
        default=0,
        nullable=False
    )

    max_attempts = db.Column(
        db.Integer,
        default=1,
        nullable=False
    )

    tab_switch_limit = db.Column(
        db.Integer,
        default=3,
        nullable=False
    )

    auto_submit_on_violation = db.Column(
        db.Boolean,
        default=True,
        nullable=False
    )

    show_result_immediately = db.Column(
        db.Boolean,
        default=True,
        nullable=False
    )

    randomize_questions = db.Column(db.Boolean, default=False, nullable=False)
    shuffle_options = db.Column(db.Boolean, default=False, nullable=False)
    question_count = db.Column(db.Integer)
    webcam_proctoring = db.Column(db.Boolean, default=False, nullable=False)
    webcam_capture_interval = db.Column(db.Integer, default=60, nullable=False)

    # Results remain private until the administrator has reviewed and
    # explicitly approved them for the public Results page.
    public_results_published = db.Column(
        db.Boolean,
        default=False,
        nullable=False
    )

    is_active = db.Column(
        db.Boolean,
        default=True,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    event = db.relationship(
        "Event",
        back_populates="online_exams"
    )

    subject = db.relationship(
        "ExamSubject",
        back_populates="exams"
    )

    questions = db.relationship(
        "ExamQuestion",
        back_populates="exam",
        cascade="all, delete-orphan",
        order_by="ExamQuestion.sort_order.asc(), ExamQuestion.id.asc()",
        lazy=True
    )

    attempts = db.relationship(
        "ExamAttempt",
        back_populates="exam",
        lazy=True
    )

    question_pools = db.relationship(
        "ExamQuestionPool",
        back_populates="exam",
        cascade="all, delete-orphan",
        order_by="ExamQuestionPool.sort_order.asc(), ExamQuestionPool.id.asc()",
        lazy=True,
    )


class ExamQuestionPool(db.Model):

    __tablename__ = "exam_question_pools"
    __table_args__ = (
        db.UniqueConstraint("exam_id", "name", name="uq_exam_question_pool_name"),
    )

    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey("online_exams.id"), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    questions_to_draw = db.Column(db.Integer, default=0, nullable=False)
    sort_order = db.Column(db.Integer, default=0, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    exam = db.relationship("OnlineExam", back_populates="question_pools")
    questions = db.relationship("ExamQuestion", back_populates="pool", lazy=True)


# ==========================================================
# EXAM QUESTIONS
# ==========================================================
class ExamQuestion(db.Model):

    __tablename__ = "exam_questions"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    exam_id = db.Column(
        db.Integer,
        db.ForeignKey("online_exams.id"),
        nullable=False
    )

    pool_id = db.Column(db.Integer, db.ForeignKey("exam_question_pools.id"))

    question_text = db.Column(
        db.Text,
        nullable=False
    )

    question_type = db.Column(
        db.String(20),
        default="mcq",
        nullable=False
    )

    option_a = db.Column(
        db.String(255),
        default="",
        nullable=False
    )

    option_b = db.Column(
        db.String(255),
        default="",
        nullable=False
    )

    option_c = db.Column(
        db.String(255),
        default="",
        nullable=False
    )

    option_d = db.Column(
        db.String(255),
        default="",
        nullable=False
    )

    correct_option = db.Column(
        db.String(1),
        default="",
        nullable=False
    )

    model_answer = db.Column(
        db.Text
    )

    explanation = db.Column(
        db.Text
    )

    marks = db.Column(
        db.Float,
        default=1,
        nullable=False
    )

    sort_order = db.Column(
        db.Integer,
        default=0,
        nullable=False
    )

    is_active = db.Column(
        db.Boolean,
        default=True,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    exam = db.relationship(
        "OnlineExam",
        back_populates="questions"
    )

    pool = db.relationship("ExamQuestionPool", back_populates="questions")

    answers = db.relationship(
        "ExamAnswer",
        back_populates="question",
        lazy=True
    )

    def options_map(self):
        return {
            "A": self.option_a,
            "B": self.option_b,
            "C": self.option_c,
            "D": self.option_d,
        }


# ==========================================================
# EXAM ATTEMPTS
# ==========================================================
class ExamAttempt(db.Model):

    __tablename__ = "exam_attempts"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    exam_id = db.Column(
        db.Integer,
        db.ForeignKey("online_exams.id"),
        nullable=False
    )

    participant_id = db.Column(
        db.Integer,
        db.ForeignKey("participants.id"),
        nullable=False
    )

    started_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    status = db.Column(db.String(20), default="in_progress", nullable=False)
    deadline_at = db.Column(db.DateTime)
    question_order_json = db.Column(db.Text)
    option_order_json = db.Column(db.Text)
    last_saved_at = db.Column(db.DateTime)

    score = db.Column(
        db.Float,
        default=0,
        nullable=False
    )

    total_marks = db.Column(
        db.Float,
        default=0,
        nullable=False
    )

    total_questions = db.Column(
        db.Integer,
        default=0,
        nullable=False
    )

    correct_answers = db.Column(
        db.Integer,
        default=0,
        nullable=False
    )

    evaluation_status = db.Column(
        db.String(30),
        default="auto_scored",
        nullable=False
    )

    violation_count = db.Column(
        db.Integer,
        default=0,
        nullable=False
    )

    answers_json = db.Column(
        db.Text
    )

    submitted_at = db.Column(
        db.DateTime
    )

    exam = db.relationship(
        "OnlineExam",
        back_populates="attempts"
    )

    participant = db.relationship(
        "Participant",
        back_populates="exam_attempts",
        lazy=True
    )

    answers = db.relationship(
        "ExamAnswer",
        back_populates="attempt",
        cascade="all, delete-orphan",
        order_by="ExamAnswer.id.asc()",
        lazy=True
    )

    proctoring_snapshots = db.relationship(
        "ExamProctoringSnapshot",
        back_populates="attempt",
        cascade="all, delete-orphan",
        order_by="ExamProctoringSnapshot.captured_at.asc()",
        lazy=True,
    )

    def answers_map(self):
        if not self.answers_json:
            return {}

        try:
            data = json.loads(self.answers_json)
        except (TypeError, ValueError):
            return {}

        return data if isinstance(data, dict) else {}

    def question_order(self):
        try:
            values = json.loads(self.question_order_json or "[]")
            return [int(value) for value in values]
        except (TypeError, ValueError):
            return []

    def option_order(self):
        try:
            values = json.loads(self.option_order_json or "{}")
            return values if isinstance(values, dict) else {}
        except (TypeError, ValueError):
            return {}


# ==========================================================
# EXAM ANSWERS
# ==========================================================
class ExamAnswer(db.Model):

    __tablename__ = "exam_answers"
    __table_args__ = (
        db.UniqueConstraint("attempt_id", "question_id", name="uq_exam_answer_attempt_question"),
    )

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    attempt_id = db.Column(
        db.Integer,
        db.ForeignKey("exam_attempts.id"),
        nullable=False
    )

    question_id = db.Column(
        db.Integer,
        db.ForeignKey("exam_questions.id"),
        nullable=False
    )

    selected_option = db.Column(
        db.String(1)
    )

    text_answer = db.Column(
        db.Text
    )

    is_correct = db.Column(
        db.Boolean
    )

    auto_score = db.Column(
        db.Float,
        default=0,
        nullable=False
    )

    manual_score = db.Column(
        db.Float
    )

    marked_for_review = db.Column(db.Boolean, default=False, nullable=False)
    saved_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    attempt = db.relationship(
        "ExamAttempt",
        back_populates="answers"
    )

    question = db.relationship(
        "ExamQuestion",
        back_populates="answers"
    )

    @property
    def awarded_score(self):
        if self.manual_score is not None:
            return float(self.manual_score)
        return float(self.auto_score or 0)


class ExamProctoringSnapshot(db.Model):

    __tablename__ = "exam_proctoring_snapshots"

    id = db.Column(db.Integer, primary_key=True)
    attempt_id = db.Column(db.Integer, db.ForeignKey("exam_attempts.id"), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    capture_type = db.Column(db.String(30), default="periodic", nullable=False)
    captured_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    attempt = db.relationship("ExamAttempt", back_populates="proctoring_snapshots")


# ==========================================================
# BLOCK MASTER
# ==========================================================
class Block(db.Model):

    __tablename__ = "blocks"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    block_name = db.Column(
        db.String(100),
        unique=True,
        nullable=False
    )

    certificate_template = db.Column(
        db.String(250),
        nullable=False
    )


# ==========================================================
# CERTIFICATE TEMPLATE
# ==========================================================
class CertificateTemplate(db.Model):

    __tablename__ = "certificate_templates"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    template_name = db.Column(
        db.String(100),
        nullable=False
    )

    certificate_type = db.Column(
        db.String(50),
        nullable=False
    )

    image_path = db.Column(
        db.String(250),
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )


# ==========================================================
# CERTIFICATE LAYOUT
# ==========================================================
class CertificateLayout(db.Model):

    __tablename__ = "certificate_layout"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    template_id = db.Column(
        db.Integer,
        db.ForeignKey("certificate_templates.id"),
        nullable=False
    )

    field_name = db.Column(
        db.String(50),
        nullable=False
    )

    text_content = db.Column(
        db.Text,
        nullable=True
    )

    x = db.Column(
        db.Integer,
        default=0
    )

    y = db.Column(
        db.Integer,
        default=0
    )

    width = db.Column(
        db.Integer,
        default=0
    )

    height = db.Column(
        db.Integer,
        default=0
    )

    font_size = db.Column(
        db.Integer,
        default=30
    )

    font_family = db.Column(
        db.String(100),
        default="Arial"
    )

    font_color = db.Column(
        db.String(20),
        default="#000000"
    )

    font_weight = db.Column(
        db.String(20),
        default="normal"
    )

    text_align = db.Column(
        db.String(20),
        default="left"
    )

    rotation = db.Column(
        db.Integer,
        default=0
    )

    visible = db.Column(
        db.Boolean,
        default=True
    )

    shape = db.Column(
        db.String(30),
        default="rectangle"
    )


# ==========================================================
# GENERATED CERTIFICATES
# ==========================================================
class Certificate(db.Model):

    __tablename__ = "certificates"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    registration_id = db.Column(
        db.Integer,
        db.ForeignKey("participants.id"),
        nullable=False
    )

    template_id = db.Column(
        db.Integer,
        db.ForeignKey("certificate_templates.id"),
        nullable=False
    )

    certificate_number = db.Column(
        db.String(50),
        unique=True
    )

    issue_date = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    pdf_file = db.Column(
        db.String(250)
    )


# ==========================================================
# CHESS TOURNAMENT MODULE
# ==========================================================
class ChessTournament(db.Model):
    __tablename__ = "chess_tournaments"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    venue = db.Column(db.String(255))
    tournament_date = db.Column(db.Date)
    organizer = db.Column(db.String(180))
    chief_arbiter = db.Column(db.String(180))
    system = db.Column(db.String(20), nullable=False, default="swiss")
    number_of_rounds = db.Column(db.Integer, nullable=False, default=5)
    max_participants = db.Column(db.Integer)
    is_published = db.Column(db.Boolean, nullable=False, default=False)
    is_locked = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    age_groups = db.relationship("ChessAgeGroup", back_populates="tournament", cascade="all, delete-orphan")


class ChessAgeGroup(db.Model):
    __tablename__ = "chess_age_groups"
    __table_args__ = (db.UniqueConstraint("tournament_id", "name", name="uq_chess_age_group_name"),)
    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey("chess_tournaments.id"), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    gender_rule = db.Column(db.String(20), default="open", nullable=False)
    admin_name = db.Column(db.String(120))
    is_published = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    tournament = db.relationship("ChessTournament", back_populates="age_groups")
    participants = db.relationship("ChessParticipant", back_populates="age_group", cascade="all, delete-orphan")
    rounds = db.relationship("ChessRound", back_populates="age_group", cascade="all, delete-orphan")


class ChessParticipant(db.Model):
    __tablename__ = "chess_participants"
    __table_args__ = (
        db.UniqueConstraint("age_group_id", "player_code", name="uq_chess_player_code"),
        db.Index("ix_chess_participant_search", "age_group_id", "name"),
    )
    id = db.Column(db.Integer, primary_key=True)
    age_group_id = db.Column(db.Integer, db.ForeignKey("chess_age_groups.id"), nullable=False, index=True)
    player_code = db.Column(db.String(32), nullable=False)
    fide_id = db.Column(db.String(30), index=True)
    name = db.Column(db.String(180), nullable=False, index=True)
    gender = db.Column(db.String(20))
    date_of_birth = db.Column(db.Date)
    district = db.Column(db.String(100), index=True)
    state = db.Column(db.String(100))
    school = db.Column(db.String(220), index=True)
    club = db.Column(db.String(180))
    mobile = db.Column(db.String(25), index=True)
    email = db.Column(db.String(180))
    photo = db.Column(db.String(250))
    status = db.Column(db.String(20), nullable=False, default="pending")
    checked_in = db.Column(db.Boolean, nullable=False, default=False)
    withdrawn = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    age_group = db.relationship("ChessAgeGroup", back_populates="participants")


class ChessRoom(db.Model):
    __tablename__ = "chess_rooms"
    __table_args__ = (db.UniqueConstraint("age_group_id", "name", name="uq_chess_room_name"),)
    id = db.Column(db.Integer, primary_key=True)
    age_group_id = db.Column(db.Integer, db.ForeignKey("chess_age_groups.id"), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False)
    board_start = db.Column(db.Integer, nullable=False, default=1)
    board_end = db.Column(db.Integer, nullable=False, default=50)


class ChessRound(db.Model):
    __tablename__ = "chess_rounds"
    __table_args__ = (db.UniqueConstraint("age_group_id", "round_number", name="uq_chess_round_number"),)
    id = db.Column(db.Integer, primary_key=True)
    age_group_id = db.Column(db.Integer, db.ForeignKey("chess_age_groups.id"), nullable=False, index=True)
    round_number = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="draft")
    is_published = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    published_at = db.Column(db.DateTime)

    age_group = db.relationship("ChessAgeGroup", back_populates="rounds")
    pairings = db.relationship("ChessPairing", back_populates="round", cascade="all, delete-orphan")


class ChessPairing(db.Model):
    __tablename__ = "chess_pairings"
    __table_args__ = (db.UniqueConstraint("round_id", "board_number", name="uq_chess_board_round"),)
    id = db.Column(db.Integer, primary_key=True)
    round_id = db.Column(db.Integer, db.ForeignKey("chess_rounds.id"), nullable=False, index=True)
    board_number = db.Column(db.Integer, nullable=False)
    table_number = db.Column(db.Integer)
    room_id = db.Column(db.Integer, db.ForeignKey("chess_rooms.id"))
    white_player_id = db.Column(db.Integer, db.ForeignKey("chess_participants.id"), nullable=False, index=True)
    black_player_id = db.Column(db.Integer, db.ForeignKey("chess_participants.id"), index=True)
    result = db.Column(db.String(30))
    score_status = db.Column(db.String(20), nullable=False, default="pending")
    remarks = db.Column(db.Text)
    submitted_by = db.Column(db.String(120))
    submitted_at = db.Column(db.DateTime)
    approved_by = db.Column(db.String(120))
    approved_at = db.Column(db.DateTime)

    round = db.relationship("ChessRound", back_populates="pairings")
    white_player = db.relationship("ChessParticipant", foreign_keys=[white_player_id])
    black_player = db.relationship("ChessParticipant", foreign_keys=[black_player_id])
    room = db.relationship("ChessRoom")


class ChessStanding(db.Model):
    __tablename__ = "chess_standings"
    __table_args__ = (db.UniqueConstraint("age_group_id", "participant_id", name="uq_chess_standing_player"),)
    id = db.Column(db.Integer, primary_key=True)
    age_group_id = db.Column(db.Integer, db.ForeignKey("chess_age_groups.id"), nullable=False, index=True)
    participant_id = db.Column(db.Integer, db.ForeignKey("chess_participants.id"), nullable=False, index=True)
    points = db.Column(db.Float, nullable=False, default=0)
    wins = db.Column(db.Integer, nullable=False, default=0)
    draws = db.Column(db.Integer, nullable=False, default=0)
    losses = db.Column(db.Integer, nullable=False, default=0)
    buchholz = db.Column(db.Float, nullable=False, default=0)
    rank = db.Column(db.Integer)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    participant = db.relationship("ChessParticipant")


class ChessOrbiter(db.Model):
    __tablename__ = "chess_orbiters"
    __table_args__ = (db.UniqueConstraint("username", name="uq_chess_orbiter_username"),)
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    username = db.Column(db.String(80), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class ChessRoomAssignment(db.Model):
    __tablename__ = "chess_room_assignments"
    __table_args__ = (db.UniqueConstraint("orbiter_id", "room_id", name="uq_chess_orbiter_room"),)
    id = db.Column(db.Integer, primary_key=True)
    orbiter_id = db.Column(db.Integer, db.ForeignKey("chess_orbiters.id"), nullable=False, index=True)
    room_id = db.Column(db.Integer, db.ForeignKey("chess_rooms.id"), nullable=False, index=True)
    orbiter = db.relationship("ChessOrbiter")
    room = db.relationship("ChessRoom")


class ChessAnnouncement(db.Model):
    __tablename__ = "chess_announcements"
    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey("chess_tournaments.id"), nullable=False, index=True)
    age_group_id = db.Column(db.Integer, db.ForeignKey("chess_age_groups.id"), index=True)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_pinned = db.Column(db.Boolean, nullable=False, default=False)
    is_published = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class ChessAuditLog(db.Model):
    __tablename__ = "chess_audit_logs"
    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey("chess_tournaments.id"), nullable=False, index=True)
    action = db.Column(db.String(100), nullable=False)
    entity_type = db.Column(db.String(50))
    entity_id = db.Column(db.Integer)
    actor = db.Column(db.String(120))
    ip_address = db.Column(db.String(64))
    details = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class ChessStaff(db.Model):
    __tablename__ = "chess_staff"
    __table_args__ = (db.UniqueConstraint("username", name="uq_chess_staff_username"),)
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    username = db.Column(db.String(80), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(30), nullable=False, default="tournament_admin")
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class ChessStaffAssignment(db.Model):
    __tablename__ = "chess_staff_assignments"
    __table_args__ = (db.UniqueConstraint("staff_id", "tournament_id", "age_group_id", name="uq_chess_staff_assignment"),)
    id = db.Column(db.Integer, primary_key=True)
    staff_id = db.Column(db.Integer, db.ForeignKey("chess_staff.id"), nullable=False, index=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey("chess_tournaments.id"), nullable=False, index=True)
    age_group_id = db.Column(db.Integer, db.ForeignKey("chess_age_groups.id"), index=True)
    staff = db.relationship("ChessStaff")


class ChessCertificate(db.Model):
    __tablename__ = "chess_certificates"
    __table_args__ = (db.UniqueConstraint("certificate_number", name="uq_chess_certificate_number"),)
    id = db.Column(db.Integer, primary_key=True)
    participant_id = db.Column(db.Integer, db.ForeignKey("chess_participants.id"), nullable=False, index=True)
    certificate_number = db.Column(db.String(64), nullable=False)
    certificate_type = db.Column(db.String(40), nullable=False, default="participation")
    file_path = db.Column(db.String(250))
    issued_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    participant = db.relationship("ChessParticipant")


class ChessNotification(db.Model):
    __tablename__ = "chess_notifications"
    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey("chess_tournaments.id"), nullable=False, index=True)
    age_group_id = db.Column(db.Integer, db.ForeignKey("chess_age_groups.id"), index=True)
    title = db.Column(db.String(200), nullable=False)
    body = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(40), nullable=False, default="announcement")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class ChessApiToken(db.Model):
    __tablename__ = "chess_api_tokens"
    __table_args__ = (db.UniqueConstraint("token_hash", name="uq_chess_api_token_hash"),)
    id = db.Column(db.Integer, primary_key=True)
    tournament_id = db.Column(db.Integer, db.ForeignKey("chess_tournaments.id"), nullable=False, index=True)
    label = db.Column(db.String(120), nullable=False)
    token_hash = db.Column(db.String(128), nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
