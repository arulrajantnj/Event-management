from datetime import datetime
import re


def extract_registration_id(scan_text):
    value = (scan_text or "").strip()
    if not value:
        return ""

    patterns = [
        r"Registration\s*Id\s*:\s*([A-Za-z0-9\-]+)",
        r"Registration\s*ID\s*:\s*([A-Za-z0-9\-]+)",
        r"/attendance/mark/([A-Za-z0-9\-]+)",
        r"reg_id=([A-Za-z0-9\-]+)",
        r'"reg_id"\s*:\s*"([A-Za-z0-9\-]+)"',
    ]

    for pattern in patterns:
        match = re.search(pattern, value, re.IGNORECASE)
        if match:
            return match.group(1).upper()

    first_line = value.splitlines()[0].strip().upper()
    if re.fullmatch(r"[A-Z0-9\-]+", first_line):
        return first_line

    return ""


def today_date():
    return datetime.utcnow().date()


def now_utc():
    return datetime.utcnow()


def serialize_dt(value):
    if not value:
        return ""
    return value.strftime("%d-%m-%Y %H:%M:%S")
