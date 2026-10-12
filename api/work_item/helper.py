import os
import requests

from api.shared.exceptions import ValidationError


def upload_work_item_document(document, category):

    cdn_url = os.getenv("CDN_URL_WEBBERKAH_DOCUMENT")
    api_key = os.getenv("API_KEY_DOCUMENT")

    if not cdn_url:
        raise ValidationError("Konfigurasi CDN document belum tersedia.")

    if not api_key:
        raise ValidationError("API key CDN document belum tersedia.")

    try:
        response = requests.post(
            f"{cdn_url}/{category}",
            files={
                "file": (
                    document.filename,
                    document.stream,
                    document.content_type
                )
            },
            headers={
                "X-API-KEY": api_key
            },
            timeout=60
        )

    except requests.RequestException:
        raise ValidationError("Gagal menghubungi CDN document.")

    if not response.ok:
        try:
            error_data = response.json()
            message = error_data.get("detail", "Gagal mengupload document.")
        except ValueError:
            message = "Gagal mengupload document."

        raise ValidationError(message)

    try:
        result = response.json()
    except ValueError:
        raise ValidationError("Response dari CDN tidak valid.")

    if not result.get("status"):
        raise ValidationError("Document gagal diupload ke CDN.")

    return result.get("url")