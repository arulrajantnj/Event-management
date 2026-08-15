from datetime import datetime

from models import db


class RegistrationSetting(db.Model):
    __tablename__ = "registration_settings"

    id = db.Column(db.Integer, primary_key=True)
    field_name = db.Column(db.String(50), unique=True, nullable=False)
    field_label = db.Column(db.String(120), nullable=False)
    enabled = db.Column(db.Boolean, nullable=False, default=True)
    required = db.Column(db.Boolean, nullable=False, default=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)


class CustomRegistrationQuestion(db.Model):
    __tablename__ = "custom_registration_questions"

    id = db.Column(db.Integer, primary_key=True)
    label = db.Column(db.String(180), nullable=False)
    field_name = db.Column(db.String(80), unique=True, nullable=False)
    question_type = db.Column(db.String(20), nullable=False, default="text")
    placeholder = db.Column(db.String(180), default="")
    default_value = db.Column(db.Text, default="")
    options = db.Column(db.Text, default="")
    required = db.Column(db.Boolean, nullable=False, default=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class Student(db.Model):
    __tablename__ = "students"

    id = db.Column(db.Integer, primary_key=True)
    registration_no = db.Column(db.String(30), unique=True, nullable=False, index=True)
    student_name = db.Column(db.String(180), nullable=False)
    student_class = db.Column(db.String(40))
    section = db.Column(db.String(40))
    emis_no = db.Column(db.String(30), unique=True)
    udise_no = db.Column(db.String(30))
    school_name = db.Column(db.String(220))
    school_block = db.Column(db.String(120))
    school_management = db.Column(db.String(160))
    school_details = db.Column(db.Text)
    mobile = db.Column(db.String(15), unique=True)
    medium = db.Column(db.String(20))
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    approval_status = db.Column(db.String(20), nullable=False, default="pending", index=True)
    rejection_reason = db.Column(db.Text, default="")
    admin_notes = db.Column(db.Text, default="")
    approved_by = db.Column(db.String(120))
    approved_date = db.Column(db.DateTime)
    registration_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    photo = db.Column(db.String(250))

    answers = db.relationship("StudentRegistrationAnswer", back_populates="student", cascade="all, delete-orphan")


class StudentRegistrationAnswer(db.Model):
    __tablename__ = "student_registration_answers"
    __table_args__ = (db.UniqueConstraint("student_id", "question_id", name="uq_student_question_answer"),)

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False, index=True)
    question_id = db.Column(db.Integer, db.ForeignKey("custom_registration_questions.id"), nullable=False)
    value = db.Column(db.Text, default="")

    student = db.relationship("Student", back_populates="answers")
    question = db.relationship("CustomRegistrationQuestion")


class StudentAuditLog(db.Model):
    __tablename__ = "student_audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), index=True)
    action = db.Column(db.String(80), nullable=False)
    details = db.Column(db.Text, default="")
    actor = db.Column(db.String(120), default="")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    student = db.relationship("Student")
