import os
import requests
from api.shared.exceptions import ValidationError
from api.utils.config import CDN_UPLOAD_URL, API_KEY_ABSENSI, CDN_UPLOAD_DOCUMENT_URL, API_KEY_DOCUMENT


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


def upload_document_to_cdn(
    file,
    category="invoice"
):
    """
    Upload document ke private CDN

    return:
    {
        "url": "...",
        "file": "...",
        "filename": "...",
        "mime_type": "..."
    }
    """

    if not file:
        raise ValidationError(
            "File wajib diupload"
        )

    upload_url = (
        f"{CDN_UPLOAD_DOCUMENT_URL}/{category}"
    )

    files = {
        "file": (
            file.filename,
            file.stream,
            file.mimetype
        )
    }

    headers = {
        "X-API-KEY":
            API_KEY_DOCUMENT
    }

    try:

        res = requests.post(
            upload_url,
            files=files,
            headers=headers,
            timeout=120
        )

    except requests.RequestException:
        raise ValidationError(
            "Gagal terhubung ke CDN"
        )

    if res.status_code != 200:
        raise ValidationError(
            f"Gagal upload file ({res.status_code})"
        )

    data = res.json()

    if not data.get("url"):
        raise ValidationError(
            "Response CDN tidak valid"
        )

    return {
        "url": data["url"],
        "file": data.get("file"),
        "filename": file.filename,
        "mime_type": file.mimetype
    }