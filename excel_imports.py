"""Shared helpers for safe, consistent spreadsheet imports."""

from io import BytesIO
import re

import pandas as pd


ALLOWED_IMPORT_EXTENSIONS = {".csv", ".xlsx", ".xls"}


def normalize_column_name(value):
    """Match common Excel heading variations to one predictable key."""
    return re.sub(r"[^a-z0-9]+", "_", str(value).replace("\ufeff", "").strip().lower()).strip("_")


def read_import_file(upload):
    """Read a supported upload and normalize its headers."""
    filename = (upload.filename or "").lower()
    extension = "." + filename.rsplit(".", 1)[-1] if "." in filename else ""
    if extension not in ALLOWED_IMPORT_EXTENSIONS:
        raise ValueError("Upload a CSV, XLSX, or XLS file.")

    try:
        frame = pd.read_csv(upload, dtype=object) if extension == ".csv" else pd.read_excel(upload, dtype=object)
    except Exception as error:
        raise ValueError("The file could not be read. Save it as a standard CSV or Excel workbook and try again.") from error

    frame.columns = [normalize_column_name(column) for column in frame.columns]
    if not len(frame.columns) or any(not column for column in frame.columns):
        raise ValueError("The first row must contain column names.")
    if frame.columns.duplicated().any():
        raise ValueError("Column names must be unique.")
    return frame


def value_from_row(row, *names):
    for name in names:
        value = row.get(normalize_column_name(name))
        if pd.notna(value):
            if isinstance(value, float) and value.is_integer():
                value = int(value)
            value = str(value).strip()
            if value and value.lower() not in {"nan", "none", "null"}:
                return value
    return ""


def workbook_response(columns, instructions, filename):
    """Create a blank Excel template plus import instructions."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        pd.DataFrame(columns=columns).to_excel(writer, index=False, sheet_name="Data")
        pd.DataFrame({"Instructions": instructions}).to_excel(writer, index=False, sheet_name="Instructions")
        worksheet = writer.sheets["Data"]
        for index, column in enumerate(columns, start=1):
            worksheet.column_dimensions[chr(64 + index)].width = max(14, min(len(column) + 4, 32))
    output.seek(0)
    return output, filename
