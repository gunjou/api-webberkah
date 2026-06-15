import os
import requests
from api.shared.exceptions import ValidationError
from api.utils.config import CDN_UPLOAD_URL, API_KEY_ABSENSI


def upload_lampiran_izin_to_cdn(file):
    """
    Upload lampiran izin ke CDN private
    return: url (string)
    """

    if not file:
        return None

    # Validasi mimetype (opsional tapi disarankan)
    if not file.mimetype.startswith("image/"):
        raise ValidationError("Lampiran harus berupa file gambar")

    upload_url = f"{CDN_UPLOAD_URL}/izin"

    files = {
        "file": (
            file.filename,
            file.stream,
            file.mimetype
        )
    }

    headers = {
        "X-API-KEY": API_KEY_ABSENSI
    }

    res = requests.post(
        upload_url,
        files=files,
        headers=headers,
        timeout=30
    )

    if res.status_code != 200:
        raise ValidationError(
            f"Gagal upload lampiran izin (status {res.status_code})"
        )

    data = res.json()
    if "url" not in data:
        raise ValidationError("Response CDN tidak mengandung url")

    return data["url"]


def upload_lampiran_izin_to_cdn(file):
    """
    Upload lampiran lembur ke CDN private
    return: url (string)
    """

    if not file:
        return None

    # Validasi mimetype (opsional tapi disarankan)
    if not file.mimetype.startswith("image/"):
        raise ValidationError("Lampiran harus berupa file gambar")

    upload_url = f"{CDN_UPLOAD_URL}/lembur"

    files = {
        "file": (
            file.filename,
            file.stream,
            file.mimetype
        )
    }

    headers = {
        "X-API-KEY": API_KEY_ABSENSI
    }

    res = requests.post(
        upload_url,
        files=files,
        headers=headers,
        timeout=30
    )

    if res.status_code != 200:
        raise ValidationError(
            f"Gagal upload lampiran izin (status {res.status_code})"
        )

    data = res.json()
    if "url" not in data:
        raise ValidationError("Response CDN tidak mengandung url")

    return data["url"]


def upload_rcc_attachment_to_cdn(
    file,
    folder="attachments"
):
    """
    Upload dokumen RCC ke CDN

    return:
    {
        "url": "...",
        "filename": "...",
        "mime_type": "..."
    }
    """

    if not file:
        raise ValidationError(
            "File wajib diupload"
        )

    upload_url = (
        f"{CDN_UPLOAD_URL}/{folder}"
    )

    files = {
        "file": (
            file.filename,
            file.stream,
            file.mimetype
        )
    }

    headers = {
        "X-API-KEY": API_KEY_ABSENSI
    }

    res = requests.post(
        upload_url,
        files=files,
        headers=headers,
        timeout=60
    )

    if res.status_code != 200:
        raise ValidationError(
            f"Gagal upload file (status {res.status_code})"
        )

    data = res.json()

    if "url" not in data:
        raise ValidationError(
            "Response CDN tidak mengandung url"
        )

    return {
        "url": data["url"],
        "filename": file.filename,
        "mime_type": file.mimetype
    }