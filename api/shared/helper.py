# api/shared/helper.py
import pytz
import uuid
from decimal import Decimal
from datetime import datetime, date, time


# === Mencari Timestamp WITA === #
def get_wita():
    wita = pytz.timezone('Asia/Makassar')
    # wib = pytz.timezone('Asia/Jakarta')
    now_wita = datetime.now(wita)
    return now_wita.replace(tzinfo=None)


def serialize_value(obj):
    if isinstance(obj, list):
        return [serialize_value(item) for item in obj]
    if isinstance(obj, dict):
        return {k: serialize_value(v) for k, v in obj.items()}
    # SQLAlchemy RowMapping
    from sqlalchemy.engine import RowMapping
    if isinstance(obj, RowMapping):
        return {k: serialize_value(v) for k, v in dict(obj).items()}
    # Decimal
    if isinstance(obj, Decimal):
        return float(obj)
    # UUID
    if isinstance(obj, uuid.UUID):
        return str(obj)
    # Datetime
    if isinstance(obj, datetime):
        return obj.isoformat()
    # Date
    if isinstance(obj, date):
        return obj.isoformat()
    # time
    if isinstance(obj, time):
        return obj.strftime("%H:%M")
    return obj