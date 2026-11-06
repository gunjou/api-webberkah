# api/purchase_request/attachment.py
"""
Menyatukan lampiran purchase request menjadi tepat satu file sebelum diupload
ke CDN, sehingga purchase_requests.attachment_path selalu berisi satu URL.

Aturan:
- 1 PDF  : file disimpan apa adanya.
- Lainnya: digabung menjadi 1 PDF. Gambar memakai format lampiran (header,
  judul LAMPIRAN, footer) dan yang berurutan disusun dalam satu halaman,
  maksimal 4 gambar per halaman.

Hasil akhir selalu PDF karena CDN dokumen menolak file gambar.

Urutan hasil mengikuti urutan file saat diupload.
"""

import os
from itertools import groupby
from io import BytesIO

from PIL import Image, ImageOps
from pypdf import PdfReader, PdfWriter
from werkzeug.datastructures import FileStorage

from api.shared.exceptions import ValidationError
from api.utils.uploader import upload_document_to_cdn

from .pdf import images_to_pdf

CDN_CATEGORY = "pekerjaan"

MAX_FILES = 10
MAX_FILE_SIZE = 10 * 1024 * 1024
MAX_IMAGE_PIXELS = 50_000_000

# Foto ponsel tertentu terbaca sebagai MPO, yaitu JPEG multi-gambar.
ALLOWED_IMAGE_FORMATS = {"JPEG", "MPO", "PNG", "WEBP"}

MAX_IMAGE_SIDE = 2000
JPEG_QUALITY = 85
PDF_MIMETYPE = "application/pdf"


def _read_upload(file):
    """Membaca dan memvalidasi isi file. Return: (jenis, bytes)."""

    name = file.filename or "tanpa nama"
    content = file.read()

    if not content:
        raise ValidationError(f"File {name} kosong.")

    if len(content) > MAX_FILE_SIZE:
        raise ValidationError(
            f"Ukuran file {name} melebihi "
            f"{MAX_FILE_SIZE // (1024 * 1024)} MB."
        )

    # Jenis file ditentukan dari isinya, bukan dari nama atau mimetype.
    if content[:1024].lstrip().startswith(b"%PDF-"):
        _validate_pdf(content, name)
        return "pdf", content

    _validate_image(content, name)
    return "image", content


def _open_pdf(content):
    """Membuka PDF. Return: (reader, locked); PDF dengan password kosong tetap terbuka."""

    reader = PdfReader(BytesIO(content))
    locked = reader.is_encrypted and not reader.decrypt("")

    return reader, locked


def _validate_pdf(content, name):
    try:
        reader, locked = _open_pdf(content)
        page_count = 0 if locked else len(reader.pages)
    except Exception:
        raise ValidationError(f"File PDF {name} rusak atau tidak dapat dibaca.")

    if locked:
        raise ValidationError(
            f"File PDF {name} terkunci password. Hapus password terlebih dahulu."
        )

    if page_count == 0:
        raise ValidationError(f"File PDF {name} tidak memiliki halaman.")


def _validate_image(content, name):
    invalid_message = f"File {name} harus berupa PDF, JPG, PNG, atau WEBP."

    try:
        with Image.open(BytesIO(content)) as image:
            image_format = image.format
            width, height = image.size
            image.verify()
    except Exception:
        raise ValidationError(invalid_message)

    if image_format not in ALLOWED_IMAGE_FORMATS:
        raise ValidationError(invalid_message)

    if width * height > MAX_IMAGE_PIXELS:
        raise ValidationError(f"Resolusi gambar {name} terlalu besar.")


def _load_rgb_image(content):
    """Membuka gambar dengan orientasi EXIF benar dan latar transparan putih."""

    with Image.open(BytesIO(content)) as source:
        image = ImageOps.exif_transpose(source).convert("RGBA")

    background = Image.new("RGB", image.size, "white")
    background.paste(image, mask=image.getchannel("A"))

    return background


def _normalize_image(content):
    """Mengubah gambar menjadi JPEG berorientasi benar dengan ukuran wajar."""

    image = _load_rgb_image(content)
    image.thumbnail((MAX_IMAGE_SIDE, MAX_IMAGE_SIDE), Image.LANCZOS)

    output = BytesIO()
    image.save(output, format="JPEG", quality=JPEG_QUALITY)

    return output.getvalue()


def _build_pdf(parts):
    """Menggabungkan PDF dan gambar sesuai urutan menjadi satu PDF."""

    writer = PdfWriter()

    for kind, group in groupby(parts, key=lambda part: part[0]):
        contents = [content for _, content in group]

        if kind == "image":
            writer.append(
                images_to_pdf([_normalize_image(item) for item in contents])
            )
            continue

        for content in contents:
            writer.append(_open_pdf(content)[0])

    output = BytesIO()
    writer.write(output)

    return output.getvalue()


def combine_attachments(files):
    """
    Menyatukan file upload menjadi satu PDF.
    Return: (bytes, nama file, mimetype).
    """

    parts = [_read_upload(file) for file in files]

    if len(parts) > 1:
        return _build_pdf(parts), "lampiran.pdf", PDF_MIMETYPE

    kind, content = parts[0]
    base_name = os.path.splitext(
        os.path.basename(files[0].filename or "")
    )[0] or "lampiran"

    if kind == "image":
        content = _build_pdf(parts)

    return content, f"{base_name}.pdf", PDF_MIMETYPE


def upload_purchase_request_attachments(files):
    """
    Memproses file lalu mengupload satu hasilnya ke CDN.
    Return: attachment_name dan attachment_path untuk body create/update.
    """

    files = [file for file in files if file and file.filename]

    if not files:
        raise ValidationError("Minimal upload 1 file lampiran.")

    if len(files) > MAX_FILES:
        raise ValidationError(f"Maksimal {MAX_FILES} file lampiran.")

    content, filename, mimetype = combine_attachments(files)

    uploaded = upload_document_to_cdn(
        FileStorage(
            stream=BytesIO(content),
            filename=filename,
            content_type=mimetype,
        ),
        category=CDN_CATEGORY,
    )

    return {
        "attachment_name": filename,
        "attachment_path": uploaded["url"],
        "mime_type": mimetype,
        "source_file_count": len(files),
    }
