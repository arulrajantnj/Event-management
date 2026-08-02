from datetime import datetime
from base64 import b64encode
from html import escape
from io import BytesIO
import os
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory

from flask import Blueprint, abort, redirect, render_template, request, send_file, session, url_for
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from models import db, OnlineExam
from offline_exam_models import (ExamModeSelection, OfflineExamAttendance, OfflineExamAuditLog,
                                 OfflineExamMark, OfflineExamStudent, QuestionPaperDownloadLog)
from student_models import Student


offline_exam_bp = Blueprint("offline_exam", __name__)


def tamil_pdf_font():
    """Register a Unicode font with Tamil glyphs and shaping support."""
    configured = os.environ.get("TAMIL_FONT_PATH")
    candidates = [
        configured,
        Path(__file__).resolve().parent / "static" / "fonts" / "NotoSansTamil-VariableFont_wdth,wght.ttf",
        Path(__file__).resolve().parent / "static" / "fonts" / "NotoSansTamil-Regular.ttf",
        Path("C:/Windows/Fonts/Nirmala.ttc"),
        Path("/usr/share/fonts/truetype/noto/NotoSansTamil-Regular.ttf"),
        Path("/usr/share/fonts/opentype/noto/NotoSansTamil-Regular.ttf"),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).is_file():
            font_name = "TamilQuestionPaper"
            if font_name not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(
                    TTFont(font_name, str(candidate), subfontIndex=0, shapable=True)
                )
            return font_name
    raise RuntimeError(
        "Tamil PDF font not found. Add static/fonts/NotoSansTamil-Regular.ttf "
        "or configure TAMIL_FONT_PATH."
    )


def draw_wrapped(pdf, text, x, y, max_width, font_name, font_size, line_height):
    """Draw complete Unicode text without clipping long questions or options."""
    words = str(text or "").split()
    lines, current = [], ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if current and pdfmetrics.stringWidth(candidate, font_name, font_size) > max_width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    for line in lines or [""]:
        pdf.drawString(x, y, line, direction="ltr", shaping=True)
        y -= line_height
    return y


def question_paper_pdf(exam):
    """Render the paper with Chromium so Tamil Unicode is shaped correctly."""
    font_path = Path(__file__).resolve().parent / "static" / "fonts" / "NotoSansTamil-VariableFont_wdth,wght.ttf"
    browser_candidates = (
        os.environ.get("CHROMIUM_PATH"),
        "C:/Program Files/Google/Chrome/Application/chrome.exe",
        "C:/Program Files (x86)/Google/Chrome/Application/chrome.exe",
        "C:/Program Files/Microsoft/Edge/Application/msedge.exe",
        "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
        shutil.which("google-chrome"),
        shutil.which("chromium"),
    )
    browser = next((candidate for candidate in browser_candidates if candidate and Path(candidate).is_file()), None)
    if not font_path.is_file() or not browser:
        raise RuntimeError("Tamil question-paper rendering requires the bundled Noto Tamil font and Chrome or Edge.")

    questions = []
    for index, question in enumerate((item for item in exam.questions if item.is_active), 1):
        options = "".join(
            f'<div class="option">{label}) {escape(str(option))}</div>'
            for label, option in zip(("A", "B", "C", "D"),
                                     (question.option_a, question.option_b, question.option_c, question.option_d))
            if option
        )
        questions.append(f'<section class="question"><div>{index}. {escape(str(question.question_text))}</div>{options}</section>')

    embedded_font = b64encode(font_path.read_bytes()).decode("ascii")
    document = f'''<!doctype html><html><head><meta charset="utf-8"><style>
        @font-face {{ font-family: "QuestionPaperTamil"; src: url("data:font/ttf;base64,{embedded_font}") format("truetype"); }}
        @page {{ size: A4; margin: 18mm 16mm; }}
        body {{ font-family: "QuestionPaperTamil", sans-serif; font-size: 12pt; line-height: 1.55; color: #000; }}
        h1 {{ font-size: 17pt; text-align: center; margin: 0 0 14mm; font-weight: 600; }}
        .question {{ break-inside: avoid; margin: 0 0 5mm; }}
        .option {{ margin-left: 8mm; }}
    </style></head><body><h1>{escape(str(exam.exam_title))}</h1>{''.join(questions)}</body></html>'''
    with TemporaryDirectory() as directory:
        source = Path(directory) / "question-paper.html"
        output = Path(directory) / "question-paper.pdf"
        source.write_text(document, encoding="utf-8")
        completed = subprocess.run(
            [browser, "--headless", "--disable-gpu", "--no-sandbox", "--no-pdf-header-footer",
             f"--print-to-pdf={output}", source.as_uri()],
            capture_output=True, text=True, timeout=45, check=False,
        )
        if completed.returncode or not output.is_file():
            raise RuntimeError("Unable to create the Tamil question paper PDF.")
        return output.read_bytes()


def operator():
    student = db.session.get(Student, session.get("student_id"))
    if not student or student.approval_status != "approved" or not student.is_active:
        return None
    return student


def log(exam_id, student_id, action, details=""):
    db.session.add(OfflineExamAuditLog(exam_id=exam_id, student_id=student_id, action=action, details=details, actor=session.get("student_id", "")))


def exam_total_marks(exam):
    return float(sum((question.marks if question.marks is not None else exam.marks_per_question)
                     for question in exam.questions if question.is_active))


@offline_exam_bp.route("/offline-exams")
def exams():
    person = operator()
    if not person: return redirect(url_for("student_registration.login"))
    return render_template("exam_mode.html", exams=OnlineExam.query.filter_by(is_active=True).all())


@offline_exam_bp.route("/offline-exams/<int:exam_id>/mode", methods=["GET", "POST"])
def select_mode(exam_id):
    person = operator(); exam = OnlineExam.query.get_or_404(exam_id)
    if not person: return redirect(url_for("student_registration.login"))
    if request.method == "POST":
        mode = request.form.get("mode", "").upper()
        if mode not in {"ONLINE", "OFFLINE"}: abort(400)
        selection = ExamModeSelection.query.filter_by(student_id=person.id, exam_id=exam.id).first()
        if not selection: selection = ExamModeSelection(student_id=person.id, exam_id=exam.id, mode=mode); db.session.add(selection)
        else: selection.mode, selection.selected_datetime = mode, datetime.utcnow()
        selection.ip_address = request.remote_addr or ""; log(exam.id, person.id, "mode_selected", mode); db.session.commit()
        return redirect(url_for("offline_exam.selection", exam_id=exam.id) if mode == "OFFLINE" else url_for("routes.exam_login"))
    return render_template("exam_mode.html", exam=exam)


@offline_exam_bp.route("/offline-exams/<int:exam_id>/students", methods=["GET", "POST"])
def selection(exam_id):
    person = operator(); exam = OnlineExam.query.get_or_404(exam_id)
    if not person: return redirect(url_for("student_registration.login"))
    if not person.udise_no: return "Your account needs a School UDISE number before offline exams can be used.", 400
    if request.method == "POST":
        selected_ids = request.form.getlist("student_ids", type=int)
        for student in Student.query.filter(Student.id.in_(selected_ids), Student.udise_no == person.udise_no, Student.approval_status == "approved", Student.is_active.is_(True)).all():
            if not OfflineExamStudent.query.filter_by(exam_id=exam.id, student_id=student.id).first():
                offline = OfflineExamStudent(exam_id=exam.id, student_id=student.id, school_udise=person.udise_no, mentor_id=person.id)
                db.session.add(offline); db.session.flush(); db.session.add(OfflineExamAttendance(offline_exam_student_id=offline.id)); log(exam.id, student.id, "offline_selected")
        selection = ExamModeSelection.query.filter_by(student_id=person.id, exam_id=exam.id).first()
        if selection: selection.submitted = True
        db.session.commit(); return redirect(url_for("offline_exam.download", exam_id=exam.id))
    selected = {item.student_id: item for item in OfflineExamStudent.query.filter_by(exam_id=exam.id, school_udise=person.udise_no).all()}
    students = Student.query.filter_by(udise_no=person.udise_no, approval_status="approved", is_active=True).order_by(Student.student_name).all()
    return render_template("offline_student_selection.html", exam=exam, operator=person, students=students, selected=selected)


@offline_exam_bp.route("/offline-exams/<int:exam_id>/download")
def download(exam_id):
    person = operator(); exam = OnlineExam.query.get_or_404(exam_id)
    if not person: return redirect(url_for("student_registration.login"))
    if not OfflineExamStudent.query.filter_by(exam_id=exam.id, school_udise=person.udise_no).first(): return redirect(url_for("offline_exam.selection", exam_id=exam.id))
    downloaded = QuestionPaperDownloadLog.query.filter_by(exam_id=exam.id, school_udise=person.udise_no).first()
    if downloaded: return render_template("offline_download.html", exam=exam, downloaded=True)
    if request.args.get("file") != "1": return render_template("offline_download.html", exam=exam, downloaded=False)
    buffer = BytesIO(question_paper_pdf(exam))
    db.session.add(QuestionPaperDownloadLog(exam_id=exam.id, school_udise=person.udise_no, mentor_id=person.id, ip_address=request.remote_addr or "")); log(exam.id, person.id, "question_paper_downloaded")
    OfflineExamStudent.query.filter_by(exam_id=exam.id, school_udise=person.udise_no).update({"status": "question_paper_issued"}); db.session.commit()
    return send_file(buffer, as_attachment=True, download_name=f"{exam.exam_code}_question_paper.pdf", mimetype="application/pdf")


@offline_exam_bp.route("/offline-exams/<int:exam_id>/marks", methods=["GET", "POST"])
def marks(exam_id):
    person = operator(); exam = OnlineExam.query.get_or_404(exam_id)
    if not person: return redirect(url_for("student_registration.login"))
    selected = db.session.query(OfflineExamStudent, Student).join(
        Student, Student.id == OfflineExamStudent.student_id
    ).filter(OfflineExamStudent.exam_id == exam.id, OfflineExamStudent.school_udise == person.udise_no).order_by(Student.student_name).all()
    if not selected: return redirect(url_for("offline_exam.selection", exam_id=exam.id))
    if request.method == "POST":
        max_marks = exam_total_marks(exam)
        for offline_student, student in selected:
            raw_score = request.form.get(f"score_{offline_student.id}", "").strip()
            if not raw_score:
                continue
            try:
                obtained_marks = float(raw_score)
            except ValueError:
                abort(400)
            if obtained_marks < 0 or obtained_marks > max_marks:
                abort(400)
            mark = OfflineExamMark.query.filter_by(exam_id=exam.id, student_id=student.id).first()
            if mark and mark.approval_status == "approved":
                continue
            if not mark:
                mark = OfflineExamMark(exam_id=exam.id, student_id=student.id, school_udise=person.udise_no, mentor_id=person.id)
                db.session.add(mark)
            mark.max_marks = max_marks
            mark.obtained_marks = obtained_marks
            mark.percentage = obtained_marks / max_marks * 100 if max_marks else 0
            mark.result = "pass" if obtained_marks >= float(exam.pass_mark or 0) else "fail"
            mark.remarks = request.form.get(f"remarks_{offline_student.id}", "").strip()
            mark.submitted = True
            mark.submitted_datetime = datetime.utcnow()
            mark.approval_status = "pending"
            mark.approved_by = None
            mark.approved_datetime = None
            mark.approval_notes = ""
            offline_student.status = "marks_submitted"
            log(exam.id, student.id, "marks_submitted_for_approval", str(obtained_marks))
        db.session.commit()
        return redirect(url_for("offline_exam.marks", exam_id=exam.id, submitted=1))
    mark_by_student = {mark.student_id: mark for mark in OfflineExamMark.query.filter_by(exam_id=exam.id, school_udise=person.udise_no).all()}
    return render_template("offline_marks.html", exam=exam, total_marks=exam_total_marks(exam),
                           selected=selected, mark_by_student=mark_by_student)
