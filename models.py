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

    whatsapp_ack_enabled = db.Column(
        db.Boolean,
        default=False,
        nullable=False
    )

    whatsapp_template = db.Column(
        db.Text
    )

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
        db.DateTime,
        default=datetime.utcnow
    )

    exam = db.relationship(
        "OnlineExam",
        back_populates="attempts"
    )

    participant = db.relationship(
        "Participant",
        lazy=True
    )

    answers = db.relationship(
        "ExamAnswer",
        back_populates="attempt",
        cascade="all, delete-orphan",
        order_by="ExamAnswer.id.asc()",
        lazy=True
    )

    def answers_map(self):
        if not self.answers_json:
            return {}

        try:
            data = json.loads(self.answers_json)
        except (TypeError, ValueError):
            return {}

        return data if isinstance(data, dict) else {}


# ==========================================================
# EXAM ANSWERS
# ==========================================================
class ExamAnswer(db.Model):

    __tablename__ = "exam_answers"

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
