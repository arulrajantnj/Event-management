from pathlib import Path

from flask import Flask

from student_registration import fetch_school_details


def test_fetch_school_details_reads_local_directory(tmp_path):
    application = Flask(__name__)
    directory = Path(tmp_path) / "school_data.xlsx"
    import pandas as pd
    pd.DataFrame([{
        "UDISE_Code": "33210100101",
        "School_Name": "Government Higher Secondary School",
        "Management": "Department of School Education",
        "Block": "Thanjavur",
        "Category": "Higher Secondary",
    }]).to_excel(directory, index=False)
    application.config["SCHOOL_DIRECTORY_FILE"] = str(directory)

    with application.app_context():
        school, error = fetch_school_details("33170100101")

    assert school is None
    assert error == "No school was found for this UDISE number."

    with application.app_context():
        school, error = fetch_school_details("33210100101")

    assert error == ""
    assert school["school_name"] == "Government Higher Secondary School"
    assert school["block"] == "Thanjavur"
    assert school["management"] == "Department of School Education"
    assert school["details"]["category"] == "Higher Secondary"


def test_registration_template_marks_custom_fields_for_school_autofill():
    template = Path("templates/student/register.html").read_text(encoding="utf-8")
    script = Path("static/js/registration.js").read_text(encoding="utf-8")

    assert 'data-registration-field="{{ question.field_name }}"' in template
    assert 'setCustomSchoolField(["block", "block_name", "school_block"], result.block)' in script
    assert 'setCustomSchoolField(["management", "school_management"], result.management)' in script
    assert "input.readOnly = true;" in script
    assert "schoolName.readOnly = true;" in script
