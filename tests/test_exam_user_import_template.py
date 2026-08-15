from admin_routes import IMPORT_TEMPLATES, exam_user_import_template
from student_registration import DEFAULT_FIELDS


def test_exam_user_template_matches_student_registration_fields():
    exam_user_columns, instructions = IMPORT_TEMPLATES["exam_users"]
    registration_columns = [field_name for field_name, _, _ in DEFAULT_FIELDS]

    assert exam_user_columns == registration_columns
    assert "matches the Student Registration form" in instructions[0]


def test_exam_user_template_appends_active_custom_question_columns(monkeypatch):
    class CustomQuestion:
        field_name = "parent_contact"
        label = "Parent Contact"
        required = True

    monkeypatch.setattr("admin_routes.active_exam_user_custom_questions", lambda: [CustomQuestion()])

    columns, instructions = exam_user_import_template()

    assert columns[-1] == "parent_contact"
    assert instructions[-1] == "Custom field: parent_contact (Parent Contact) — required."
