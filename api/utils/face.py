import os
import uuid
import requests
import face_recognition
from api.shared.exceptions import ValidationError
from api.utils.config import engine
from sqlalchemy import text


def get_pegawai_face_path(id_pegawai: int):
    sql = text("""
        SELECT img_path
        FROM auth_pegawai
        WHERE id_pegawai = :id
          AND status = 1
        LIMIT 1
    """)
    with engine.connect() as conn:
        return conn.execute(sql, {"id": id_pegawai}).scalar()


def verify_face(id_pegawai: int, image_file):
    """
    Verifikasi wajah pegawai (FIXED & STABIL)
    """

    img_url = get_pegawai_face_path(id_pegawai)
    if not img_url:
        raise ValidationError("Data wajah pegawai belum tersedia")

    ref_path = f"/tmp/{uuid.uuid4().hex}_ref.jpg"
    live_path = f"/tmp/{uuid.uuid4().hex}_live.jpg"

    # download wajah referensi
    res = requests.get(img_url, timeout=10)
    if res.status_code != 200:
        raise ValidationError("Gagal mengambil data wajah pegawai")

    with open(ref_path, "wb") as f:
        f.write(res.content)

    image_file.stream.seek(0)
    image_file.save(live_path)

    try:
        known_image = face_recognition.load_image_file(ref_path)
        unknown_image = face_recognition.load_image_file(live_path)

        known_encodings = face_recognition.face_encodings(known_image)
        unknown_encodings = face_recognition.face_encodings(unknown_image)

        if not known_encodings or not unknown_encodings:
            raise ValidationError("Wajah tidak terdeteksi dengan jelas")

        result = face_recognition.compare_faces(
            [known_encodings[0]],
            unknown_encodings[0],
            tolerance=0.6
        )[0]

        # 🧠 pastikan return bool python
        return bool(result)

    finally:
        if os.path.exists(ref_path):
            os.remove(ref_path)
        if os.path.exists(live_path):
            os.remove(live_path)
