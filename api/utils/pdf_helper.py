from datetime import datetime, date
import re


def _safe_filename(value):
    value = str(value or "").strip()
    value = re.sub(r'[\\/:*?"<>|]', "-", value)
    value = re.sub(r"\s+", " ", value)

    return value.strip(" .-") or "Tanpa Nama"


def _format_filename_date(value):
    if not value:
        return "Tanpa-Tanggal"

    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value).date()
        except ValueError:
            return "Tanpa-Tanggal"

    if isinstance(value, datetime):
        value = value.date()

    if isinstance(value, date):
        return value.strftime("%d-%m-%Y")

    return "Tanpa-Tanggal"