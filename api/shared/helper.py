# api/shared/helper.py
import os
import random
import string
import pytz
import uuid
import requests
from PIL import Image
import face_recognition
from decimal import Decimal
from dotenv import load_dotenv
from datetime import datetime, date, time
from werkzeug.datastructures import FileStorage

from api.shared.exceptions import ValidationError

load_dotenv()

# === Konfigurasi CDN === #
CDN_UPLOAD_URL = os.getenv("CDN_UPLOAD_URL")
API_KEY_ABSENSI = os.getenv("API_KEY_ABSENSI")


# === Mencari Timestamp WITA === #
def get_wita():
    wita = pytz.timezone('Asia/Makassar')
    # wib = pytz.timezone('Asia/Jakarta')
    now_wita = datetime.now(wita)
    return now_wita.replace(tzinfo=None)


def generate_recovery_code(length: int = 6):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

def _validate_image_file(file: FileStorage):
    if not file:
        raise ValidationError("File gambar wajib dikirim")

    if not file.mimetype.startswith("image/"):
        raise ValidationError("File harus berupa gambar")

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

def extract_face_grayscale(file: FileStorage, temp_dir="tmp_faces"):
    os.makedirs(temp_dir, exist_ok=True)

    # simpan file sementara
    temp_filename = f"{uuid.uuid4().hex}.jpg"
    temp_path = os.path.join(temp_dir, temp_filename)
    file.save(temp_path)

    # load image
    image = face_recognition.load_image_file(temp_path)
    face_locations = face_recognition.face_locations(image)

    if not face_locations:
        os.remove(temp_path)
        raise ValidationError("Tidak ditemukan wajah pada gambar")

    # ambil wajah pertama
    top, right, bottom, left = face_locations[0]
    face_image = image[top:bottom, left:right]

    pil_image = Image.fromarray(face_image).convert("L")  # grayscale

    face_filename = f"{uuid.uuid4().hex}.jpg"
    face_path = os.path.join(temp_dir, face_filename)
    pil_image.save(face_path)

    os.remove(temp_path)
    return face_path

def upload_face_to_cdn(file_path: str):
    upload_url = f"{CDN_UPLOAD_URL}/wajah"

    with open(file_path, "rb") as f:
        files = {
            "file": (
                os.path.basename(file_path),
                f,
                "image/jpeg"
            )
        }
        headers = {
            "X-API-KEY": API_KEY_ABSENSI
        }
        res = requests.post(
            upload_url,
            files=files,
            headers=headers
        )

    if res.status_code != 200:
        raise ValidationError(
            f"Gagal upload foto ke CDN ({res.status_code}): {res.text}"
        )

    data = res.json()
    if "url" not in data:
        raise ValidationError("Response CDN tidak mengandung url")

    return data["url"]