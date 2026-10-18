
from api.shared.exceptions import ValidationError, NotFoundError
from api.work_item.helper import upload_work_item_document

from .query import *


# ============================================================================ #
#                         #SECTION - LEGAL DOCUMENTS                           #
# ============================================================================ #

def get_legal_document_list_service(filters):

    search = filters.get("search")

    if search is not None:
        search = search.strip() or None

    return get_legal_document_list(
        search=search
    )


def create_legal_document_service(body, created_by, document=None):

    # ---------------------------- Document Name ------------------------------- #

    document_name = body.get("document_name")

    if not document_name or not document_name.strip():
        raise ValidationError("Nama dokumen wajib diisi")

    document_name = document_name.strip()

    if len(document_name) > 150:
        raise ValidationError("Nama dokumen maksimal 150 karakter")

    # -------------------------------- Document -------------------------------- #

    if not document:
        raise ValidationError("File dokumen wajib diunggah")

    if not document.filename or not document.filename.strip():
        raise ValidationError("File dokumen tidak valid")

    # ------------------------------- Description ------------------------------ #

    description = body.get("description")

    if description is not None:
        description = description.strip() or None

    # ----------------------------- Upload to CDN ------------------------------ #

    file_url = upload_work_item_document(
        document,
        "legal-document"
    )

    if not file_url:
        raise ValidationError("URL dokumen tidak diterima dari CDN")

    # ---------------------------------- Create -------------------------------- #

    return create_legal_document(
        document_name=document_name,
        description=description,
        file_url=file_url,
        created_by=created_by
    )


def get_legal_document_detail_service(id_legal_document):

    if not id_legal_document:
        raise ValidationError("ID dokumen wajib diisi")

    document = get_legal_document_by_id(
        id_legal_document
    )

    if not document:
        raise NotFoundError("Dokumen legalitas tidak ditemukan")

    return document


def update_legal_document_service(
    id_legal_document,
    body,
    updated_by,
    document=None
):

    if not id_legal_document:
        raise ValidationError("ID dokumen wajib diisi")

    # --------------------------------- Get Data -------------------------------- #

    existing_document = get_legal_document_by_id(
        id_legal_document
    )

    if not existing_document:
        raise NotFoundError("Dokumen legalitas tidak ditemukan")

    # ------------------------------ Validate Input ---------------------------- #

    document_name = body.get("document_name")
    description = body.get("description")

    update_description = "description" in body

    if (
        document_name is None
        and not update_description
        and document is None
    ):
        raise ValidationError(
            "Minimal satu data dokumen harus diperbarui"
        )

    # ------------------------------ Document Name ----------------------------- #

    if document_name is not None:

        if not document_name.strip():
            raise ValidationError("Nama dokumen tidak boleh kosong")

        document_name = document_name.strip()

        if len(document_name) > 150:
            raise ValidationError(
                "Nama dokumen maksimal 150 karakter"
            )

    # ------------------------------- Description ------------------------------ #

    if description is not None:
        description = description.strip() or None

    # ----------------------------- Upload New File ---------------------------- #

    file_url = None

    if document:

        if not document.filename or not document.filename.strip():
            raise ValidationError("File dokumen tidak valid")

        file_url = upload_work_item_document(
            document,
            "legal-document"
        )

        if not file_url:
            raise ValidationError("URL dokumen tidak diterima dari CDN")

    # ---------------------------------- Update -------------------------------- #

    return update_legal_document(
        id_legal_document=id_legal_document,
        document_name=document_name,
        description=description,
        file_url=file_url,
        updated_by=updated_by,
        update_description=update_description
    )


def delete_legal_document_service(
    id_legal_document,
    updated_by
):

    if not id_legal_document:
        raise ValidationError("ID dokumen wajib diisi")

    # --------------------------------- Get Data -------------------------------- #

    existing_document = get_legal_document_by_id(
        id_legal_document
    )

    if not existing_document:
        raise NotFoundError("Dokumen legalitas tidak ditemukan")

    # ------------------------------- Soft Delete ------------------------------- #

    delete_legal_document(
        id_legal_document=id_legal_document,
        updated_by=updated_by
    )

    return {
        "id_legal_document": id_legal_document
    }
