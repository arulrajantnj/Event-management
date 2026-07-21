from pathlib import Path
import os

from werkzeug.security import generate_password_hash


os.environ.setdefault("SECRET_KEY", "test-secret-key-that-is-long-and-not-for-production")
os.environ.setdefault("ADMIN_USERNAME", "security-test-admin")
os.environ.setdefault("ADMIN_PASSWORD_HASH", generate_password_hash("security-test-password"))

from app import app
from models import ExamAnswer, ExamAttempt, OnlineExam


def test_exam_portal_lifecycle_contract():
    rules = {str(rule) for rule in app.url_map.iter_rules()}
    assert "/api/exam/<int:exam_id>/attempt/<int:attempt_id>/autosave" in rules
    assert "/api/exam/<int:exam_id>/attempt/<int:attempt_id>/proctoring" in rules

    assert hasattr(ExamAttempt, "status")
    assert hasattr(ExamAttempt, "deadline_at")
    assert hasattr(ExamAttempt, "question_order_json")
    assert hasattr(ExamAttempt, "option_order_json")
    assert hasattr(ExamAnswer, "marked_for_review")
    assert hasattr(OnlineExam, "randomize_questions")
    assert hasattr(OnlineExam, "shuffle_options")
    assert hasattr(OnlineExam, "webcam_proctoring")

    template = (Path(__file__).parents[1] / "templates" / "take_exam.html").read_text(encoding="utf-8")
    assert 's.review?"palette-review":hasAnswer(id)?"palette-answered":"palette-unanswered"' in template
    assert 'if(index===currentIndex)button.classList.add("current")' in template
    assert "Mark for Review &amp; Next" in template
    assert "Save &amp; Next" in template
