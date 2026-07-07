import os
import logging
from datetime import datetime

from PIL import Image, ImageDraw, ImageFont, ImageOps

import qrcode

from models import db, Block, Participant

# reuse constants from certificate_generator if available, otherwise set defaults
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
STATIC = os.path.join(BASE_DIR, "static")
TEMPLATE_FOLDER = os.path.join(STATIC, "certificate_templates")
UPLOAD_FOLDER = os.path.join(STATIC, "uploads")
CERT_FOLDER = os.path.join(STATIC, "generated_certificates")
QR_FOLDER = os.path.join(STATIC, "generated_qr")
FONT_FOLDER = os.path.join(BASE_DIR, "fonts")

os.makedirs(CERT_FOLDER, exist_ok=True)
os.makedirs(QR_FOLDER, exist_ok=True)

TITLE_FONT = os.path.join(FONT_FOLDER, "timesbd.ttf")
TEXT_FONT = os.path.join(FONT_FOLDER, "arial.ttf")

from PIL import ImageFont

def load_font(path, size):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        logging.warning("Font not found: %s", path)
        return ImageFont.load_default()

FONT_TITLE = load_font(TITLE_FONT, 56)
FONT_NAME = load_font(TITLE_FONT, 52)
FONT_TEXT = load_font(TEXT_FONT, 30)

# minimal helpers copied from certificate_generator
from certificate_generator import (
    get_template,
    load_teacher_photo,
    generate_qr,
    center_text
)


def generate_certificate(participant_or_reg_id):
    if isinstance(participant_or_reg_id, Participant):
        participant = participant_or_reg_id
    else:
        participant = Participant.query.filter_by(reg_id=str(participant_or_reg_id)).first()

    if not participant:
        logging.error("Participant not found: %s", participant_or_reg_id)
        return {"success": False, "error": "participant_not_found"}

    template_path = get_template(participant)

    try:
        cert = Image.open(template_path).convert("RGB")
    except Exception:
        logging.exception("Failed to open template: %s", template_path)
        return {"success": False, "error": "template_load_failed"}

    draw = ImageDraw.Draw(cert)
    width, height = cert.size

    # Draw texts
    try:
        center_text(draw, "Certificate of Participation", FONT_TITLE, int(height * 0.14), width)
        center_text(draw, participant.teacher_name or "", FONT_NAME, int(height * 0.28), width)

        y = int(height * 0.40)
        line_height = FONT_TEXT.getsize("Ay")[1]

        for txt in (participant.designation, participant.subject, participant.school_name, participant.school_area):
            if not txt:
                continue
            center_text(draw, txt, FONT_TEXT, y, width)
            y += line_height + 6

        date_text = datetime.utcnow().strftime("%d %b %Y")
        draw.text((60, height - 100), f"Issued: {date_text}", font=FONT_TEXT, fill="black")
        draw.text((60, height - 60), f"Reg ID: {participant.reg_id}", font=FONT_TEXT, fill="black")
    except Exception:
        logging.exception("Failed to draw text")

    # Teacher photo
    try:
        teacher_img = load_teacher_photo(participant.photo)
        if teacher_img:
            tx = int(width * 0.08)
            ty = int(height * 0.18)
            cert.paste(teacher_img, (tx, ty))
    except Exception:
        logging.exception("Failed to paste teacher photo")

    # QR
    try:
        qr_img, qr_file = generate_qr(participant.reg_id)
        qx = width - qr_img.width - 60
        qy = height - qr_img.height - 60
        cert.paste(qr_img, (qx, qy))
    except Exception:
        logging.exception("Failed to generate/paste QR")
        qr_file = None

    # Save
    try:
        filename = f"{participant.reg_id}.png"
        out_path = os.path.join(CERT_FOLDER, filename)
        cert.save(out_path)

        participant.certificate_pdf = os.path.join("generated_certificates", filename)
        if qr_file:
            participant.qr_code = os.path.join("generated_qr", os.path.basename(qr_file))
        participant.certificate_generated = True

        db.session.add(participant)
        db.session.commit()

        return {
            "success": True,
            "certificate_path": out_path,
            "certificate_rel": participant.certificate_pdf,
            "qr_path": qr_file,
            "qr_rel": participant.qr_code,
            "participant_id": participant.id,
        }
    except Exception:
        logging.exception("Failed to save certificate or update DB")
        return {"success": False, "error": "save_failed"}
