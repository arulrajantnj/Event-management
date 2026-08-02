from datetime import datetime

from models import db


class ExamModeSelection(db.Model):
    __tablename__ = "exam_mode_selection"
    __table_args__ = (db.UniqueConstraint("student_id", "exam_id", name="uq_exam_mode_student_exam"),)
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False, index=True)
    exam_id = db.Column(db.Integer, db.ForeignKey("online_exams.id"), nullable=False, index=True)
    mode = db.Column(db.String(10), nullable=False)
    selected_datetime = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    submitted = db.Column(db.Boolean, nullable=False, default=False)
    ip_address = db.Column(db.String(64), default="")


class OfflineExamStudent(db.Model):
    __tablename__ = "offline_exam_students"
    __table_args__ = (db.UniqueConstraint("exam_id", "student_id", name="uq_offline_exam_student"),)
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey("online_exams.id"), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False, index=True)
    school_udise = db.Column(db.String(30), nullable=False, index=True)
    mentor_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    status = db.Column(db.String(30), nullable=False, default="selected_offline")
    selected_datetime = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class OfflineExamAttendance(db.Model):
    __tablename__ = "offline_exam_attendance"
    __table_args__ = (db.UniqueConstraint("offline_exam_student_id", name="uq_offline_attendance_student"),)
    id = db.Column(db.Integer, primary_key=True)
    offline_exam_student_id = db.Column(db.Integer, db.ForeignKey("offline_exam_students.id"), nullable=False)
    attendance_status = db.Column(db.String(10), nullable=False, default="present")
    marked_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class OfflineExamMark(db.Model):
    __tablename__ = "offline_exam_marks"
    __table_args__ = (db.UniqueConstraint("exam_id", "student_id", name="uq_offline_mark_student"),)
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey("online_exams.id"), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False, index=True)
    school_udise = db.Column(db.String(30), nullable=False, index=True)
    mentor_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    max_marks = db.Column(db.Float, nullable=False, default=0)
    obtained_marks = db.Column(db.Float, nullable=False, default=0)
    percentage = db.Column(db.Float, nullable=False, default=0)
    result = db.Column(db.String(10), default="")
    remarks = db.Column(db.Text, default="")
    submitted = db.Column(db.Boolean, nullable=False, default=False)
    submitted_datetime = db.Column(db.DateTime)
    approval_status = db.Column(db.String(20), nullable=False, default="draft", index=True)
    approved_by = db.Column(db.String(120))
    approved_datetime = db.Column(db.DateTime)
    approval_notes = db.Column(db.Text, default="")


class QuestionPaperDownloadLog(db.Model):
    __tablename__ = "questionpaper_download_log"
    __table_args__ = (db.UniqueConstraint("exam_id", "school_udise", name="uq_question_paper_school"),)
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey("online_exams.id"), nullable=False, index=True)
    school_udise = db.Column(db.String(30), nullable=False, index=True)
    mentor_id = db.Column(db.Integer, db.ForeignKey("students.id"), nullable=False)
    download_datetime = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    ip_address = db.Column(db.String(64), default="")


class OfflineExamAuditLog(db.Model):
    __tablename__ = "offline_exam_audit_logs"
    id = db.Column(db.Integer, primary_key=True)
    exam_id = db.Column(db.Integer, db.ForeignKey("online_exams.id"), nullable=False, index=True)
    student_id = db.Column(db.Integer, db.ForeignKey("students.id"))
    action = db.Column(db.String(80), nullable=False)
    details = db.Column(db.Text, default="")
    actor = db.Column(db.String(120), default="")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
