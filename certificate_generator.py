import logging
import os
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont, ImageOps
import qrcode

from models import db, CertificateLayout, CertificateTemplate, Participant


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s"
)


BASE_DIR = os.path.abspath(os.path.dirname(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATE_FOLDER = os.path.join(STATIC_DIR, "certificate_templates")
UPLOAD_FOLDER = os.path.join(STATIC_DIR, "uploads")
CERT_FOLDER = os.path.join(STATIC_DIR, "generated_certificates")
QR_FOLDER = os.path.join(STATIC_DIR, "generated_qr")
STATIC_FONT_FOLDER = os.path.join(STATIC_DIR, "fonts")
LEGACY_FONT_FOLDER = os.path.join(BASE_DIR, "fonts")
SYSTEM_FONT_FOLDER = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")

DEFAULT_CERTIFICATE_TEMPLATE = "winner.png"
DEFAULT_FONT_FAMILY = "Arial"
DEFAULT_FONT_SIZE = 24
DEFAULT_TEXT_COLOR = "#000000"

FONT_FILE_ALIASES = {
    "arial": "arial.ttf",
    "times new roman": "times.ttf",
    "verdana": "verdana.ttf",
    "georgia": "georgia.ttf",
    "latha": "Nirmala.ttc",
    "vijaya": "Nirmala.ttc",
    "nirmala ui": "Nirmala.ttc",
    "noto sans tamil": "Nirmala.ttc",
}

os.makedirs(CERT_FOLDER, exist_ok=True)
os.makedirs(QR_FOLDER, exist_ok=True)


def get_active_template():
    template = CertificateTemplate.query.order_by(
        CertificateTemplate.id
    ).first()

    if template:
        return template

    return None


def get_template(participant=None):
    template_record = get_active_template()

    if template_record and template_record.image_path:
        template_path = os.path.join(
            TEMPLATE_FOLDER,
            template_record.image_path
        )

        if os.path.exists(template_path):
            return template_path

    fallback = os.path.join(
        TEMPLATE_FOLDER,
        DEFAULT_CERTIFICATE_TEMPLATE
    )

    if os.path.exists(fallback):
        return fallback

    return os.path.join(
        TEMPLATE_FOLDER,
        "participation.png"
    )


def get_layout_fields(template_id):
    return CertificateLayout.query.filter_by(
        template_id=template_id
    ).all()


def load_teacher_photo(filename):
    if not filename:
        return None

    filepath = os.path.join(UPLOAD_FOLDER, filename)

    if not os.path.exists(filepath):
        return None

    try:
        return Image.open(filepath).convert("RGB")
    except Exception:
        logging.warning("Unable to open teacher photo: %s", filepath)
        return None


def generate_qr(registration_id):
    qr = qrcode.QRCode(
        version=2,
        box_size=10,
        border=2
    )

    qr.add_data(registration_id)
    qr.make(fit=True)

    img = qr.make_image(
        fill_color="black",
        back_color="white"
    ).convert("RGB")

    qr_file = os.path.join(
        QR_FOLDER,
        registration_id + ".png"
    )

    img.save(qr_file)

    return img, qr_file


def load_font_by_family(font_family, size):
    candidates = []
    family_name = (font_family or DEFAULT_FONT_FAMILY).strip()
    family_key = family_name.lower()

    aliased_file = FONT_FILE_ALIASES.get(family_key)
    if aliased_file:
        candidates.append(os.path.join(STATIC_FONT_FOLDER, aliased_file))
        candidates.append(os.path.join(LEGACY_FONT_FOLDER, aliased_file))
        candidates.append(os.path.join(SYSTEM_FONT_FOLDER, aliased_file))

    for folder in (STATIC_FONT_FOLDER, LEGACY_FONT_FOLDER, SYSTEM_FONT_FOLDER):
        for ext in (".ttf", ".otf", ".ttc"):
            candidates.append(
                os.path.join(folder, family_name + ext)
            )
            candidates.append(
                os.path.join(folder, family_name.replace(" ", "_") + ext)
            )

    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                logging.warning("Unable to load font file: %s", path)

    try:
        return ImageFont.truetype("arial.ttf", size)
    except Exception:
        return ImageFont.load_default()


def fit_image_to_box(image, width, height):
    if width <= 0 or height <= 0:
        return image

    return ImageOps.fit(
        image,
        (width, height),
        method=Image.Resampling.LANCZOS
    )


def build_shape_mask(width, height, shape):
    mask = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(mask)

    if shape == "circle":
        draw.ellipse((0, 0, width - 1, height - 1), fill=255)
    elif shape == "rounded":
        radius = max(8, min(width, height) // 6)
        draw.rounded_rectangle(
            (0, 0, width - 1, height - 1),
            radius=radius,
            fill=255
        )
    else:
        draw.rectangle((0, 0, width - 1, height - 1), fill=255)

    return mask


def paste_box_image(canvas, image, field):
    width = max(1, int(field.width or image.width))
    height = max(1, int(field.height or image.height))
    x = int(field.x or 0)
    y = int(field.y or 0)
    shape = (field.shape or "rectangle").lower()

    fitted = fit_image_to_box(image, width, height).convert("RGBA")
    mask = build_shape_mask(width, height, shape)
    fitted.putalpha(mask)
    canvas.paste(fitted, (x, y), fitted)


def draw_photo_placeholder(canvas, field):
    width = max(1, int(field.width or 100))
    height = max(1, int(field.height or 120))
    x = int(field.x or 0)
    y = int(field.y or 0)
    shape = (field.shape or "rounded").lower()

    overlay = Image.new("RGBA", (width, height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)
    mask = build_shape_mask(width, height, shape)

    # Soft cream fill keeps the placeholder visible without fighting the template.
    fill = Image.new("RGBA", (width, height), (246, 239, 228, 210))
    overlay.paste(fill, (0, 0), mask)

    border_color = "#b98a2f"
    if shape == "circle":
        draw.ellipse((1, 1, width - 2, height - 2), outline=border_color, width=3)
    elif shape == "rounded":
        radius = max(8, min(width, height) // 6)
        draw.rounded_rectangle(
            (1, 1, width - 2, height - 2),
            radius=radius,
            outline=border_color,
            width=3
        )
    else:
        draw.rectangle((1, 1, width - 2, height - 2), outline=border_color, width=3)

    font = load_font_by_family("Arial", max(12, min(width, height) // 6))
    label = "PHOTO"
    text_width, text_height = measure_text(draw, label, font)
    draw.text(
        ((width - text_width) // 2, (height - text_height) // 2),
        label,
        font=font,
        fill="#7f5d20"
    )

    canvas.paste(overlay, (x, y), overlay)


def cover_photo_area(canvas, field):
    width = max(1, int(field.width or 100))
    height = max(1, int(field.height or 120))
    x = int(field.x or 0)
    y = int(field.y or 0)
    shape = (field.shape or "rounded").lower()

    overlay = Image.new("RGBA", (width, height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)

    if shape == "circle":
        draw.ellipse((0, 0, width - 1, height - 1), fill=(244, 238, 228, 245))
    elif shape == "rounded":
        radius = max(8, min(width, height) // 6)
        draw.rounded_rectangle(
            (0, 0, width - 1, height - 1),
            radius=radius,
            fill=(244, 238, 228, 245)
        )
    else:
        draw.rectangle((0, 0, width - 1, height - 1), fill=(244, 238, 228, 245))

    canvas.paste(overlay, (x, y), overlay)


def measure_text(draw, text, font):
    left, top, right, bottom = draw.textbbox(
        (0, 0),
        text,
        font=font
    )
    return right - left, bottom - top


def center_text(draw, text, font, y, width):
    text_width, _ = measure_text(draw, text, font)
    x = (width - text_width) // 2
    draw.text((x, y), text, font=font, fill="black")


def draw_text_field(canvas, field, text):
    if field.visible is False:
        return

    value = "" if text is None else str(text)
    width = max(1, int(field.width or 200))
    height = max(1, int(field.height or 40))
    x = int(field.x or 0)
    y = int(field.y or 0)
    font_size = int(field.font_size or DEFAULT_FONT_SIZE)
    font = load_font_by_family(field.font_family, font_size)
    fill = field.font_color or DEFAULT_TEXT_COLOR
    text_align = (field.text_align or "left").lower()

    overlay = Image.new("RGBA", (width, height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)
    text_width, text_height = measure_text(draw, value, font)

    if text_align == "center":
        text_x = max(0, (width - text_width) // 2)
    elif text_align == "right":
        text_x = max(0, width - text_width)
    else:
        text_x = 0

    text_y = max(0, (height - text_height) // 2)

    draw.text(
        (text_x, text_y),
        value,
        font=font,
        fill=fill
    )

    rotation = int(field.rotation or 0)
    if rotation:
        overlay = overlay.rotate(
            -rotation,
            expand=True,
            resample=Image.Resampling.BICUBIC
        )

    canvas.paste(overlay, (x, y), overlay)


def field_value_map(participant):
    return {
        "teacher_name": participant.teacher_name or "",
        "salutation": participant.salutation or "",
        "designation": participant.designation or "",
        "subject": participant.subject or "",
        "school_name": participant.school_name or "",
        "school_area": participant.school_area or "",
        "block": participant.block or "",
        "registration_id": participant.reg_id or "",
        "date": datetime.utcnow().strftime("%d %b %Y"),
    }


def render_layout(canvas, participant, fields):
    values = field_value_map(participant)
    requires_photo = True

    if getattr(participant, "event", None) is not None:
        requires_photo = participant.event.requires_photo

    teacher_photo_field = None
    qr_field = None

    for field in fields:
        if field.field_name == "teacher_photo":
            teacher_photo_field = field
            continue

        if field.field_name == "qr_code":
            qr_field = field
            continue

        if field.field_name in values:
            draw_text_field(
                canvas,
                field,
                values[field.field_name]
            )

    if teacher_photo_field and teacher_photo_field.visible is not False:
        if requires_photo:
            teacher_image = load_teacher_photo(participant.photo)
            if teacher_image:
                paste_box_image(canvas, teacher_image, teacher_photo_field)
            else:
                draw_photo_placeholder(canvas, teacher_photo_field)
        else:
            cover_photo_area(canvas, teacher_photo_field)

    qr_file = None
    if qr_field and qr_field.visible is not False:
        qr_image, qr_file = generate_qr(participant.reg_id)
        paste_box_image(canvas, qr_image, qr_field)

    return qr_file


def render_fallback(canvas, participant):
    draw = ImageDraw.Draw(canvas)
    width, height = canvas.size
    requires_photo = True

    if getattr(participant, "event", None) is not None:
        requires_photo = participant.event.requires_photo

    title_font = load_font_by_family("Times New Roman", 56)
    name_font = load_font_by_family("Times New Roman", 52)
    text_font = load_font_by_family("Arial", 30)

    def center_text(text, font, y):
        text_width, _ = measure_text(draw, text, font)
        x = (width - text_width) // 2
        draw.text((x, y), text, font=font, fill="black")

    center_text("Certificate of Participation", title_font, int(height * 0.14))
    center_text(participant.teacher_name or "", name_font, int(height * 0.28))

    y = int(height * 0.40)
    for value in (
        participant.designation,
        participant.subject,
        participant.school_name,
        participant.school_area,
    ):
        if value:
            center_text(value, text_font, y)
            y += 36

    date_text = datetime.utcnow().strftime("%d %b %Y")
    draw.text((60, height - 100), f"Issued: {date_text}", font=text_font, fill="black")
    draw.text((60, height - 60), f"Reg ID: {participant.reg_id}", font=text_font, fill="black")

    if requires_photo:
        teacher_img = load_teacher_photo(participant.photo)
        if teacher_img:
            teacher_img = ImageOps.contain(teacher_img, (220, 260))
            canvas.paste(teacher_img, (int(width * 0.08), int(height * 0.18)))

    qr_img, qr_file = generate_qr(participant.reg_id)
    qr_img = ImageOps.contain(qr_img, (180, 180))
    canvas.paste(
        qr_img,
        (width - qr_img.width - 60, height - qr_img.height - 60)
    )
    return qr_file


def generate_certificate(participant_or_reg_id):
    if isinstance(participant_or_reg_id, Participant):
        participant = participant_or_reg_id
    else:
        participant = Participant.query.filter_by(
            reg_id=str(participant_or_reg_id)
        ).first()

    if not participant:
        logging.error("Participant not found: %s", participant_or_reg_id)
        return {"success": False, "error": "participant_not_found"}

    template_record = get_active_template()
    template_path = get_template(participant)

    try:
        certificate = Image.open(template_path).convert("RGBA")
    except Exception:
        logging.exception("Failed to open template: %s", template_path)
        return {"success": False, "error": "template_load_failed"}

    qr_file = None

    try:
        if template_record:
            fields = get_layout_fields(template_record.id)
        else:
            fields = []

        if fields:
            qr_file = render_layout(certificate, participant, fields)
        else:
            qr_file = render_fallback(certificate, participant)
    except Exception:
        logging.exception("Failed to render certificate layout")
        return {"success": False, "error": "render_failed"}

    try:
        filename = f"{participant.reg_id}.png"
        out_path = os.path.join(CERT_FOLDER, filename)
        certificate.convert("RGB").save(out_path)

        participant.certificate_pdf = os.path.join(
            "generated_certificates",
            filename
        )
        if qr_file:
            participant.qr_code = os.path.join(
                "generated_qr",
                os.path.basename(qr_file)
            )
        participant.certificate_generated = True

        db.session.add(participant)
        db.session.commit()

        return {
            "success": True,
            "certificate_path": out_path,
            "certificate_rel": participant.certificate_pdf,
            "qr_path": qr_file,
            "qr_rel": participant.qr_code,
            "participant_id": participant.id
        }
    except Exception:
        logging.exception("Failed to save certificate or update DB")
        return {"success": False, "error": "save_failed"}
