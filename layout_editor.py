import os

from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from werkzeug.utils import secure_filename
from models import db, CertificateTemplate, CertificateLayout, Participant

layout_bp = Blueprint("layout", __name__)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
FONT_DIR = os.path.join(STATIC_DIR, "fonts")
ALLOWED_FONT_EXTENSIONS = {".ttf", ".otf", ".woff", ".woff2"}
DEFAULT_PLACEHOLDER_FONT_SIZE = 14
DEFAULT_APPRECIATION_TEXT = "In appreciation of your valuable participation and contribution."

os.makedirs(FONT_DIR, exist_ok=True)


DEFAULT_FIELDS = [
    "teacher_photo",
    "teacher_name",
    "salutation",
    "designation",
    "subject",
    "school_name",
    "school_area",
    "block",
    "registration_id",
    "qr_code",
    "date",
    "appreciation_text",
]


BUILT_IN_FONTS = [
    {"name": "Arial", "file": None},
    {"name": "Times New Roman", "file": None},
    {"name": "Verdana", "file": None},
    {"name": "Georgia", "file": None},
    {"name": "Noto Sans Tamil", "file": None},
    {"name": "Latha", "file": None},
    {"name": "Vijaya", "file": None},
]


def list_uploaded_fonts():
    fonts = []

    if not os.path.isdir(FONT_DIR):
        return fonts

    for filename in sorted(os.listdir(FONT_DIR)):
        name, ext = os.path.splitext(filename)

        if ext.lower() not in ALLOWED_FONT_EXTENSIONS:
            continue

        fonts.append({
            "name": name.replace("_", " "),
            "file": filename
        })

    return fonts


def available_fonts():
    font_names = set()
    fonts = []

    for font in BUILT_IN_FONTS + list_uploaded_fonts():
        key = font["name"].lower()

        if key in font_names:
            continue

        font_names.add(key)
        fonts.append(font)

    return fonts


def ensure_default_template():
    template = CertificateTemplate.query.order_by(
        CertificateTemplate.id
    ).first()

    if template:
        return template

    template_dir = os.path.join("static", "certificate_templates")
    preferred = [
        "participation.png",
        "winner.png",
        "perambalur.png"
    ]

    image_path = next(
        (
            filename
            for filename in preferred
            if os.path.exists(os.path.join(template_dir, filename))
        ),
        None
    )

    if not image_path and os.path.isdir(template_dir):
        image_path = next(
            (
                filename
                for filename in os.listdir(template_dir)
                if filename.lower().endswith((".png", ".jpg", ".jpeg"))
            ),
            None
        )

    if not image_path:
        image_path = "winner.png"

    template = CertificateTemplate(
        template_name="Default Certificate",
        certificate_type="Participation",
        image_path=image_path
    )

    db.session.add(template)
    db.session.commit()

    return template


def ensure_default_layout(template_id):
    for field_name in DEFAULT_FIELDS:
        exists = CertificateLayout.query.filter_by(
            template_id=template_id,
            field_name=field_name
        ).first()

        if not exists:
            is_appreciation = field_name == "appreciation_text"
            db.session.add(
                CertificateLayout(
                    template_id=template_id,
                    field_name=field_name,
                    width=500 if is_appreciation else 120,
                    height=80 if is_appreciation else 28,
                    font_size=DEFAULT_PLACEHOLDER_FONT_SIZE,
                    font_family="Noto Sans Tamil",
                    text_align="center" if is_appreciation else "left",
                    text_content=(
                        DEFAULT_APPRECIATION_TEXT
                        if is_appreciation
                        else None
                    ),
                    visible=is_appreciation
                )
            )
        else:
            if exists.font_size is None or exists.font_size >= 28:
                exists.font_size = DEFAULT_PLACEHOLDER_FONT_SIZE

            if not exists.width:
                exists.width = 120

            if not exists.height:
                exists.height = 28

            if not exists.font_family:
                exists.font_family = "Noto Sans Tamil"

            if (
                field_name not in {"appreciation_text", "teacher_photo", "qr_code"}
                and exists.visible is not False
                and float(exists.y or 0) <= 3
            ):
                exists.visible = False

    db.session.commit()


# ==========================================================
# OPEN LAYOUT EDITOR
# ==========================================================

@layout_bp.route("/layout-editor")
def layout_editor_default():

    template = ensure_default_template()
    ensure_default_layout(template.id)

    return redirect(
        url_for("layout.layout_editor", template_id=template.id)
    )

@layout_bp.route("/layout-editor/<int:template_id>")
def layout_editor(template_id):

    template = CertificateTemplate.query.get_or_404(template_id)

    ensure_default_layout(template.id)

    template_file = os.path.join(
        STATIC_DIR,
        "certificate_templates",
        template.image_path or ""
    )

    if not os.path.exists(template_file):
        fallback = next(
            (
                filename
                for filename in os.listdir(os.path.join(STATIC_DIR, "certificate_templates"))
                if filename.lower().endswith((".png", ".jpg", ".jpeg"))
            ),
            None
        )

        if fallback:
            template.image_path = fallback
            template_file = os.path.join(
                STATIC_DIR,
                "certificate_templates",
                fallback
            )
            db.session.add(template)
            db.session.commit()

    fields = CertificateLayout.query.filter_by(
        template_id=template.id
    ).all()

    template_image_url = url_for(
        "static",
        filename=f"certificate_templates/{template.image_path}",
        v=int(os.path.getmtime(template_file)) if os.path.exists(template_file) else 0
    )

    return render_template(
        "certificates/layout_editor.html",
        template=template,
        fields=fields,
        fonts=available_fonts(),
        template_image_url=template_image_url
    )


# ==========================================================
# GET LAYOUT DATA
# ==========================================================

@layout_bp.route("/api/layout/<int:template_id>")
def get_layout(template_id):

    fields = CertificateLayout.query.filter_by(
        template_id=template_id
    ).all()

    return jsonify([
        {
            "id": f.id,
            "template_id": f.template_id,
            "field_name": f.field_name,
            "text_content": f.text_content,
            "x": f.x,
            "y": f.y,
            "width": f.width,
            "height": f.height,
            "font_size": f.font_size,
            "font_family": f.font_family,
            "font_color": f.font_color,
            "font_weight": f.font_weight,
            "text_align": f.text_align,
            "shape": f.shape,
            "rotation": f.rotation,
            "visible": f.visible
        }
        for f in fields
    ])


# ==========================================================
# FONT DATA
# ==========================================================

@layout_bp.route("/api/fonts")
def get_fonts():
    return jsonify(available_fonts())


@layout_bp.route("/api/upload-font", methods=["POST"])
def upload_font():
    file = request.files.get("font")

    if not file or not file.filename:
        return jsonify({
            "success": False,
            "error": "No font file selected"
        }), 400

    filename = secure_filename(file.filename)
    _, ext = os.path.splitext(filename)

    if ext.lower() not in ALLOWED_FONT_EXTENSIONS:
        return jsonify({
            "success": False,
            "error": "Upload a .ttf, .otf, .woff, or .woff2 font file"
        }), 400

    file.save(os.path.join(FONT_DIR, filename))

    return jsonify({
        "success": True,
        "font": {
            "name": os.path.splitext(filename)[0].replace("_", " "),
            "file": filename
        }
    })


# ==========================================================
# SAVE LAYOUT
# ==========================================================

@layout_bp.route("/api/save-layout", methods=["POST"])
def save_layout():

    data = request.get_json()
    template_id = data.get("template_id")
    fields = data.get("fields", [])

    for item in fields:

        field = CertificateLayout.query.filter_by(
            template_id=template_id,
            field_name=item["field_name"]
        ).first()

        if not field:
            field = CertificateLayout(
                template_id=template_id,
                field_name=item["field_name"]
            )
            db.session.add(field)

        field.x = item.get("x", 0)
        field.y = item.get("y", 0)
        field.width = item.get("width", 200)
        field.height = item.get("height", 50)
        field.font_size = item.get("font_size", DEFAULT_PLACEHOLDER_FONT_SIZE)
        field.font_family = item.get("font_family", "Noto Sans Tamil")
        field.font_color = item.get("font_color", "#000000")
        field.font_weight = item.get("font_weight", "normal")
        field.text_align = item.get("text_align", "left")
        field.shape = item.get("shape", "rectangle")
        field.rotation = item.get("rotation", 0)
        field.visible = item.get("visible", True)
        field.text_content = item.get("text_content")

    # A layout change makes every previously checked preview stale. Require the
    # administrator to regenerate and approve certificates again.
    Participant.query.filter(Participant.certificate_approved.is_(True)).update(
        {
            Participant.certificate_approved: False,
            Participant.certificate_approved_at: None,
        },
        synchronize_session=False,
    )
    db.session.commit()

    return jsonify({"success": True})

    # ==========================================================
# CREATE DEFAULT LAYOUT
# ==========================================================

@layout_bp.route("/create-default-layout/<int:template_id>")
def create_default_layout(template_id):

    ensure_default_layout(template_id)

    return jsonify({
        "success": True,
        "message": "Default layout created"
    })
