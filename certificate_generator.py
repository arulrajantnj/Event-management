import logging
import os
import re
import unicodedata
from datetime import datetime
from html.parser import HTMLParser

from PIL import Image, ImageColor, ImageDraw, ImageFont, ImageOps
import qrcode

try:
    import freetype
    import uharfbuzz as hb
except ImportError:  # The application still starts, but complex scripts use Pillow fallback.
    freetype = None
    hb = None

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
EDITOR_CANVAS_SIZE = (1100, 700)


class RichTextParser(HTMLParser):
    def __init__(self, default_style):
        super().__init__()
        self.styles = [default_style]
        self.runs = []

    def handle_starttag(self, tag, attrs):
        style = dict(self.styles[-1])
        attributes = dict(attrs)
        if tag == "br":
            self.runs.append(("\n", style))
            return
        if tag == "font":
            style["color"] = attributes.get("color", style["color"])
            style["font_family"] = attributes.get("face", style["font_family"])
            if attributes.get("size", "").isdigit():
                scale = {1: .65, 2: .8, 3: 1, 4: 1.2, 5: 1.5, 6: 2, 7: 3}
                style["font_size"] = max(6, round(style["font_size"] * scale.get(int(attributes["size"]), 1)))
        css = attributes.get("style", "")
        for name, value in re.findall(r"([\w-]+)\s*:\s*([^;]+)", css):
            if name.lower() == "color": style["color"] = value.strip()
            if name.lower() == "font-family": style["font_family"] = value.strip(" '\"")
            if name.lower() == "font-size":
                match = re.search(r"[\d.]+", value)
                if match: style["font_size"] = max(6, round(float(match.group())))
            if name.lower() == "text-decoration" and "underline" in value: style["underline"] = True
        if tag == "u": style["underline"] = True
        if tag in ("div", "p") and self.runs: self.runs.append(("\n", dict(style)))
        self.styles.append(style)

    def handle_endtag(self, tag):
        if len(self.styles) > 1: self.styles.pop()

    def handle_data(self, data):
        if data:
            self.runs.append((data.replace("\u00a0", " "), dict(self.styles[-1])))


def rich_text_runs(value, field, values):
    html = str(value or "")
    for tag, replacement in values.items():
        html = html.replace("{{" + tag + "}}", str(replacement))
    default_style = {
        "color": field.font_color or DEFAULT_TEXT_COLOR,
        "font_family": field.font_family or DEFAULT_FONT_FAMILY,
        "font_size": int(field.font_size or DEFAULT_FONT_SIZE),
        "underline": False,
    }
    parser = RichTextParser(default_style)
    parser.feed(html)
    return parser.runs, html

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


def font_path_by_family(font_family):
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
            return path
    return None


def load_font_by_family(font_family, size):
    path = font_path_by_family(font_family)
    if path:
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


def draw_photo_border(canvas, field, color="#b98a2f", border_width=3):
    width = max(1, int(field.width or 100))
    height = max(1, int(field.height or 120))
    x = int(field.x or 0)
    y = int(field.y or 0)
    shape = (field.shape or "rectangle").lower()
    inset = min(border_width // 2, max(0, min(width, height) // 2))
    bounds = (inset, inset, width - 1 - inset, height - 1 - inset)

    overlay = Image.new("RGBA", (width, height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)

    if shape == "circle":
        draw.ellipse(bounds, outline=color, width=border_width)
    elif shape == "rounded":
        radius = max(8, min(width, height) // 6)
        draw.rounded_rectangle(bounds, radius=radius, outline=color, width=border_width)
    else:
        draw.rectangle(bounds, outline=color, width=border_width)

    canvas.paste(overlay, (x, y), overlay)


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


def needs_complex_shaping(text):
    return any("\u0b80" <= character <= "\u0bff" for character in str(text))


def grapheme_clusters(text):
    clusters = []
    for character in str(text):
        if (
            not clusters
            or (
                not unicodedata.category(character).startswith("M")
                and not clusters[-1].endswith(("\u0bcd", "\u200d"))
            )
        ):
            clusters.append(character)
        else:
            clusters[-1] += character
    return clusters


def shape_text(text, font_family, font_size):
    path = font_path_by_family(font_family)
    if not text or not path or hb is None or freetype is None:
        return None
    with open(path, "rb") as font_file:
        font_data = font_file.read()
    hb_face = hb.Face(font_data)
    hb_font = hb.Font(hb_face)
    hb_font.scale = (int(font_size * 64), int(font_size * 64))
    hb.ot_font_set_funcs(hb_font)
    buffer = hb.Buffer()
    buffer.add_str(str(text))
    buffer.guess_segment_properties()
    hb.shape(hb_font, buffer)
    return path, buffer.glyph_infos, buffer.glyph_positions


def shaped_text_width(text, font_family, font_size):
    shaped = shape_text(text, font_family, font_size)
    if not shaped:
        return None
    return max(0, round(sum(position.x_advance for position in shaped[2]) / 64))


def styled_text_width(draw, text, style, font):
    if needs_complex_shaping(text):
        width = shaped_text_width(text, style["font_family"], style["font_size"])
        if width is not None:
            return width
    return measure_text(draw, text, font)[0]


def draw_shaped_text(image, position, text, font_family, font_size, color):
    shaped = shape_text(text, font_family, font_size)
    if not shaped:
        return False
    path, infos, positions = shaped
    face = freetype.Face(path)
    face.set_pixel_sizes(0, int(font_size))
    pen_x = float(position[0])
    baseline = float(position[1]) + int(font_size)
    red, green, blue = ImageColor.getrgb(color)
    for info, glyph_position in zip(infos, positions):
        face.load_glyph(info.codepoint, freetype.FT_LOAD_RENDER)
        glyph = face.glyph
        bitmap = glyph.bitmap
        if bitmap.width and bitmap.rows:
            alpha = Image.frombytes("L", (bitmap.width, bitmap.rows), bytes(bitmap.buffer))
            glyph_image = Image.new("RGBA", alpha.size, (red, green, blue, 0))
            glyph_image.putalpha(alpha)
            glyph_x = round(pen_x + glyph_position.x_offset / 64 + glyph.bitmap_left)
            glyph_y = round(baseline - glyph_position.y_offset / 64 - glyph.bitmap_top)
            image.alpha_composite(glyph_image, (glyph_x, glyph_y))
        pen_x += glyph_position.x_advance / 64
        baseline -= glyph_position.y_advance / 64
    return True


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
    style = {"font_family": field.font_family or DEFAULT_FONT_FAMILY, "font_size": font_size}
    text_align = (field.text_align or "left").lower()

    overlay = Image.new("RGBA", (width, height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)
    lines = []
    for paragraph in value.splitlines() or [""]:
        words = paragraph.split()
        if not words:
            lines.append("")
            continue
        line = words[0]
        for word in words[1:]:
            candidate = f"{line} {word}"
            if styled_text_width(draw, candidate, style, font) <= width:
                line = candidate
            else:
                lines.append(line)
                line = word
        lines.append(line)

    line_height = max(1, measure_text(draw, "Ag", font)[1] + max(2, font_size // 5))
    lines = lines[:max(1, height // line_height)]
    total_height = len(lines) * line_height
    text_y = max(0, (height - total_height) // 2)

    for line in lines:
        text_width = styled_text_width(draw, line, style, font)
        if text_align == "center":
            text_x = max(0, (width - text_width) // 2)
        elif text_align == "right":
            text_x = max(0, width - text_width)
        else:
            text_x = 0
        if not (needs_complex_shaping(line) and draw_shaped_text(
            overlay, (text_x, text_y), line, style["font_family"], font_size, fill
        )):
            draw.text((text_x, text_y), line, font=font, fill=fill)
        text_y += line_height

    rotation = int(field.rotation or 0)
    if rotation:
        overlay = overlay.rotate(
            -rotation,
            expand=True,
            resample=Image.Resampling.BICUBIC
        )

    canvas.paste(overlay, (x, y), overlay)


def draw_rich_text_field(canvas, field, html, values):
    if field.visible is False:
        return
    width = max(1, int(field.width or 200))
    height = max(1, int(field.height or 40))
    font_size = int(field.font_size or DEFAULT_FONT_SIZE)
    runs, resolved_html = rich_text_runs(html, field, values)
    align_match = re.search(
        r"(?:text-align\s*:\s*|align=[\"']?)(left|center|right|justify)",
        resolved_html,
        re.IGNORECASE,
    )
    text_align = align_match.group(1).lower() if align_match else (field.text_align or "left").lower()
    overlay = Image.new("RGBA", (width, height), (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)
    lines, line, line_width = [], [], 0
    for text, style in runs:
        for token in re.findall(r"\n|[^\S\n]+|[^\s]+", text):
            if token == "\n":
                lines.append(line); line, line_width = [], 0
                continue
            font = load_font_by_family(style["font_family"], style.get("font_size", font_size))
            token_width = styled_text_width(draw, token, style, font)
            if not token.isspace() and token_width > width:
                if line:
                    lines.append(line); line, line_width = [], 0
                chunk = ""
                for cluster in grapheme_clusters(token):
                    candidate = chunk + cluster
                    if chunk and styled_text_width(draw, candidate, style, font) > width:
                        chunk_width = styled_text_width(draw, chunk, style, font)
                        lines.append([(chunk, style, font, chunk_width)])
                        chunk = cluster
                    else:
                        chunk = candidate
                token = chunk
                token_width = styled_text_width(draw, token, style, font)
            if line and not token.isspace() and line_width + token_width > width:
                lines.append(line); line, line_width = [], 0
                token = token.lstrip()
                token_width = styled_text_width(draw, token, style, font)
            if token:
                line.append((token, style, font, token_width)); line_width += token_width
    if line or not lines: lines.append(line)
    visible_lines, used_height = [], 0
    for items in lines:
        largest = max([item[1].get("font_size", font_size) for item in items] or [font_size])
        line_height = largest + max(3, largest // 4)
        if visible_lines and used_height + line_height > height: break
        visible_lines.append((items, line_height)); used_height += line_height
    y = max(0, (height - used_height) // 2)
    for line_index, (items, line_height) in enumerate(visible_lines):
        used = sum(item[3] for item in items)
        x = (width - used) // 2 if text_align == "center" else (width - used if text_align == "right" else 0)
        expandable_spaces = sum(1 for item in items if item[0].isspace())
        extra_space = (
            (width - used) / expandable_spaces
            if text_align == "justify" and line_index < len(visible_lines) - 1 and expandable_spaces
            else 0
        )
        for token, style, font, token_width in items:
            if not (needs_complex_shaping(token) and draw_shaped_text(
                overlay,
                (x, y),
                token,
                style["font_family"],
                style["font_size"],
                style["color"],
            )):
                draw.text((x, y), token, font=font, fill=style["color"])
            if style.get("underline") and token.strip():
                underline_y = y + style.get("font_size", font_size) + 1
                draw.line((x, underline_y, x + token_width, underline_y), fill=style["color"], width=1)
            x += token_width + (extra_space if token.isspace() else 0)
        y += line_height
    rotation = int(field.rotation or 0)
    if rotation:
        overlay = overlay.rotate(-rotation, expand=True, resample=Image.Resampling.BICUBIC)
    canvas.paste(overlay, (int(field.x or 0), int(field.y or 0)), overlay)


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
        elif field.field_name == "appreciation_text":
            draw_rich_text_field(canvas, field, field.text_content or "", values)

    if teacher_photo_field and teacher_photo_field.visible is not False:
        if requires_photo:
            teacher_image = load_teacher_photo(participant.photo)
            if teacher_image:
                paste_box_image(canvas, teacher_image, teacher_photo_field)
                draw_photo_border(canvas, teacher_photo_field)
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
            photo_x = int(width * 0.08)
            photo_y = int(height * 0.18)
            canvas.paste(teacher_img, (photo_x, photo_y))
            draw = ImageDraw.Draw(canvas)
            draw.rectangle(
                (photo_x, photo_y, photo_x + teacher_img.width - 1, photo_y + teacher_img.height - 1),
                outline="#b98a2f",
                width=3,
            )

    qr_img, qr_file = generate_qr(participant.reg_id)
    qr_img = ImageOps.contain(qr_img, (180, 180))
    canvas.paste(
        qr_img,
        (width - qr_img.width - 60, height - qr_img.height - 60)
    )
    return qr_file


def generate_certificate(participant_or_reg_id, persist=True, output_filename=None):
    if isinstance(participant_or_reg_id, Participant) or (
        not persist and hasattr(participant_or_reg_id, "reg_id")
    ):
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

    original_size = certificate.size
    certificate = certificate.resize(EDITOR_CANVAS_SIZE, Image.Resampling.LANCZOS)
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
        if certificate.size != original_size:
            certificate = certificate.resize(original_size, Image.Resampling.LANCZOS)
        filename = output_filename or f"{participant.reg_id}.png"
        out_path = os.path.join(CERT_FOLDER, filename)
        certificate.convert("RGB").save(out_path)

        certificate_rel = os.path.join("generated_certificates", filename)
        qr_rel = os.path.join("generated_qr", os.path.basename(qr_file)) if qr_file else None
        if persist:
            participant.certificate_pdf = certificate_rel
            if qr_rel:
                participant.qr_code = qr_rel
            participant.certificate_generated = True
            db.session.add(participant)
            db.session.commit()

        return {
            "success": True,
            "certificate_path": out_path,
            "certificate_rel": certificate_rel,
            "qr_path": qr_file,
            "qr_rel": qr_rel,
            "participant_id": participant.id if persist else None
        }
    except Exception:
        logging.exception("Failed to save certificate or update DB")
        return {"success": False, "error": "save_failed"}
