from api.shared.exceptions import ValidationError, NotFoundError
from api.work_item.helper import upload_work_item_document
from .query import *


# ============================================================================ #
#                           #SECTION - COMPLETION (BA)                         #
# ============================================================================ #

def get_completion_list_service(filters):

    stage = filters.get("stage", "ACTIVE")

    page = filters.get("page")
    per_page = filters.get("per_page")

    # =========================== Pagination Validation ========================== #

    if page is not None and page < 1:
        raise ValidationError("Page harus lebih besar atau sama dengan 1.")

    if per_page is not None and per_page < 25:
        raise ValidationError("Per page minimal 25.")

    if per_page is not None and per_page > 100:
        raise ValidationError("Per page maksimal 100.")

    if (page is None) != (per_page is None):
        raise ValidationError("Page dan per page harus diisi bersamaan.")

    # ==================== Active tidak menggunakan pagination =================== #

    if stage == "ACTIVE":
        page = None
        per_page = None

    return get_completion_list(
        stage=stage,
        search=filters.get("search"),
        id_work_item=filters.get("id_work_item"),
        id_client=filters.get("id_client"),
        page=page,
        per_page=per_page
    )


def create_completion_service(body, created_by, document=None):

    id_work_item = body.get("id_work_item")

    if not id_work_item:
        raise ValidationError("Work Item wajib dipilih")

    ba_number = body.get("ba_number")

    if not ba_number or not ba_number.strip():
        raise ValidationError("Nomor BA wajib diisi")

    work_item = get_work_item_by_id(id_work_item)

    if not work_item:
        raise NotFoundError("Work Item tidak ditemukan")

    # -----------------------------------------------------------------------------
    # BA hanya dapat dibuat ketika Work Item berada pada
    # stage CONTRACT
    # -----------------------------------------------------------------------------

    if work_item.get("current_stage") != "CONTRACT":
        raise ValidationError("BA hanya dapat dibuat ketika Work Item berada pada tahap CONTRACT")

    # -------------- BA hanya dapat dibuat jika progress sudah 100% -------------- #

    progress_percent = work_item.get("progress_percent") or 0

    if float(progress_percent) != 100:
        raise ValidationError("BA hanya dapat dibuat jika progress pekerjaan sudah mencapai 100%")

    # ---------------- Hanya satu BA aktif untuk setiap Work Item ---------------- #

    existing_completion = get_completion_by_work_item(id_work_item)

    if existing_completion:
        raise ValidationError("Work Item sudah memiliki BA aktif")

    # ----------------------- Nomor BA tidak boleh duplikat ---------------------- #

    duplicate = get_completion_by_number(ba_number.strip())

    if duplicate:
        raise ValidationError("Nomor BA sudah digunakan")

    # -----------------------------------------------------------------------------
    # BA Date
    #
    # Jika tidak dikirim, gunakan tanggal hari ini.
    # -----------------------------------------------------------------------------

    ba_date = body.get("ba_date")

    if not ba_date:
        ba_date = get_wita().date()

    # -------------------------- Upload document ke CDN -------------------------- #

    document_url = None

    if document:
        document_url = upload_work_item_document(
            document,
            "ba"
        )

    # --------------------------------- Create BA -------------------------------- #

    return create_completion(
        id_work_item=id_work_item,
        ba_number=ba_number.strip(),
        ba_date=ba_date,
        document_url=document_url,
        notes=body.get("notes"),
        created_by=created_by
    )


def get_completion_detail_service(id_completion):

    if not id_completion:
        raise ValidationError("ID BA wajib diisi")

    completion = get_completion_detail(id_completion)

    if not completion:
        raise NotFoundError("BA tidak ditemukan")

    return completion


def update_completion_service(id_completion, data, updated_by, document=None):

    if not id_completion:
        raise ValidationError("ID BA wajib diisi")

    # --------------------------------- Ambil BA --------------------------------- #

    completion = get_completion_by_id(id_completion)

    if not completion:
        raise NotFoundError("BA tidak ditemukan")

    id_work_item = data.get("id_work_item")
    ba_number = data.get("ba_number")
    ba_date = data.get("ba_date")
    notes = data.get("notes")

    # ------------------------------ Validasi input ------------------------------ #

    if not id_work_item:
        raise ValidationError("Work Item wajib dipilih")

    if not ba_number or not ba_number.strip():
        raise ValidationError("Nomor BA wajib diisi")

    if not ba_date:
        raise ValidationError("Tanggal BA wajib diisi")

    # ---------------------------- Validasi Work Item ---------------------------- #

    work_item = get_work_item_by_id(id_work_item)

    if not work_item:
        raise NotFoundError("Work Item tidak ditemukan")

    # -----------------------------------------------------------------------------
    # BA hanya dapat diedit ketika Work Item berada pada stage BA
    # -----------------------------------------------------------------------------

    if work_item.get("current_stage") != "BA":
        raise ValidationError(
            "BA hanya dapat diperbarui ketika Work Item berada pada tahap BA"
        )

    # ------------------------- Progress harus tetap 100% ------------------------ #

    progress_percent = work_item.get("progress_percent") or 0

    if float(progress_percent) != 100:
        raise ValidationError(
            "BA hanya dapat diperbarui jika progress pekerjaan sudah mencapai 100%"
        )

    # ----------------------- Upload document baru jika ada ---------------------- #

    document_url = None

    if document:
        document_url = upload_work_item_document(
            document,
            "ba"
        )

    # --------------------------------- Update BA -------------------------------- #

    return update_completion(
        id_completion=id_completion,
        id_work_item=id_work_item,
        ba_number=ba_number.strip(),
        ba_date=ba_date,
        document_url=document_url,
        notes=notes.strip() if notes else None,
        updated_by=updated_by
    )


def delete_completion_service(id_completion, updated_by):

    if not id_completion:
        raise ValidationError("ID BA wajib diisi")

    completion = get_completion_by_id(id_completion)

    if not completion:
        raise NotFoundError("BA tidak ditemukan")

    id_work_item = completion.get("id_work_item")

    work_item = get_work_item_by_id(id_work_item)

    if not work_item:
        raise NotFoundError("Work Item tidak ditemukan")

    # BA hanya dapat dihapus ketika Work Item
    # masih berada pada stage BA
    if work_item.get("current_stage") != "BA":
        raise ValidationError(
            "BA hanya dapat dihapus ketika Work Item berada pada tahap BA"
        )

    return delete_completion(
        id_completion=id_completion,
        id_work_item=id_work_item,
        updated_by=updated_by
    )


def get_completion_options_service(context=None):

    return get_completion_options(
        context=context
    )