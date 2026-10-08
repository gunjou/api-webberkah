from api.shared.exceptions import ValidationError, NotFoundError
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


def create_completion_service(body, created_by):

    id_work_item = body.get("id_work_item")

    if not id_work_item:
        raise ValidationError("Work Item wajib dipilih")

    ba_number = body.get("ba_number")

    if not ba_number or not ba_number.strip():
        raise ValidationError("Nomor BA wajib diisi")

    ba_date = body.get("ba_date")

    if not ba_date:
        raise ValidationError("Tanggal BA wajib diisi")

    work_item = get_work_item_by_id(id_work_item)

    if not work_item:
        raise NotFoundError("Work Item tidak ditemukan")

    # BA hanya dapat dibuat ketika Work Item berada pada stage CONTRACT
    if work_item.get("current_stage") != "CONTRACT":
        raise ValidationError("BA hanya dapat dibuat ketika Work Item berada pada tahap CONTRACT")

    # BA hanya dapat dibuat jika pekerjaan sudah 100%
    progress_percent = work_item.get("progress_percent") or 0

    if progress_percent != 100:
        raise ValidationError("BA hanya dapat dibuat jika progress pekerjaan sudah mencapai 100%")

    # Hanya BA aktif yang diperhitungkan
    existing_completion = get_completion_by_work_item(id_work_item)

    if existing_completion:
        raise ValidationError("Work Item sudah memiliki BA aktif")

    # Hanya nomor BA aktif yang tidak boleh duplikat
    duplicate = get_completion_by_number(ba_number)

    if duplicate:
        raise ValidationError("Nomor BA sudah digunakan")

    completion_date = body.get("completion_date")

    if completion_date and completion_date < ba_date:
        raise ValidationError("Tanggal penyelesaian tidak boleh lebih kecil dari tanggal BA")

    return create_completion(
        id_work_item=id_work_item,
        ba_number=ba_number.strip(),
        ba_date=ba_date,
        completion_date=completion_date,
        document_url=body.get("document_url"),
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


def update_completion_service(id_completion, data, updated_by):

    if not id_completion:
        raise ValidationError("ID BA wajib diisi")

    completion = get_completion_by_id(id_completion)

    if not completion:
        raise NotFoundError("BA tidak ditemukan")

    id_work_item = data.get("id_work_item")
    ba_number = data.get("ba_number")
    ba_date = data.get("ba_date")
    completion_date = data.get("completion_date")
    document_url = data.get("document_url")
    notes = data.get("notes")

    if not id_work_item:
        raise ValidationError("Work Item wajib dipilih")

    if not ba_number or not ba_number.strip():
        raise ValidationError("Nomor BA wajib diisi")

    if not ba_date:
        raise ValidationError("Tanggal BA wajib diisi")

    work_item = get_work_item_by_id(id_work_item)

    if not work_item:
        raise NotFoundError("Work Item tidak ditemukan")

    duplicate = get_completion_by_number(
        ba_number=ba_number.strip(),
        exclude_id=id_completion
    )

    if duplicate:
        raise ValidationError("Nomor BA sudah digunakan")

    existing_completion = get_completion_by_work_item(
        id_work_item=id_work_item,
        exclude_id=id_completion
    )

    if existing_completion:
        raise ValidationError("Work Item sudah memiliki BA aktif")

    if completion_date and completion_date < ba_date:
        raise ValidationError("Tanggal penyelesaian tidak boleh lebih kecil dari tanggal BA")

    return update_completion(
        id_completion=id_completion,
        id_work_item=id_work_item,
        ba_number=ba_number.strip(),
        ba_date=ba_date,
        completion_date=completion_date,
        document_url=document_url.strip() if document_url else None,
        notes=notes.strip() if notes else None,
        updated_by=updated_by
    )

    # return get_completion_detail(id_completion)


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