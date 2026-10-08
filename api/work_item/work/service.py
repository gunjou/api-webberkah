from api.shared.exceptions import ValidationError, NotFoundError
from .query import *


# ============================================================================ #
#                         #SECTION - WORK ITEM                                 #
# ============================================================================ #

def get_work_item_list_service(filters: dict):

    stage = filters.get("stage", "ACTIVE")

    page = filters.get("page")
    per_page = filters.get("per_page")

    # ============================ VALIDATE PAGINATION =========================== #

    if page is not None and page < 1:
        raise ValidationError("Page harus lebih besar atau sama dengan 1.")

    if per_page is not None and per_page < 25:
        raise ValidationError("Per page minimal 25.")

    if per_page is not None and per_page > 100:
        raise ValidationError("Per page maksimal 100.")

    # ==================== PAGE DAN PER PAGE HARUS BERPASANGAN =================== #

    if (page is None) != (per_page is None):
        raise ValidationError("Page dan per page harus diisi bersamaan.")

    # ==================== ACTIVE TIDAK MENGGUNAKAN PAGINATION =================== #

    if stage == "ACTIVE":
        page = None
        per_page = None

    return get_work_item_list(
        stage=stage,
        current_stage=filters.get("current_stage"),
        search=filters.get("search"),
        work_type=filters.get("work_type"),
        id_client=filters.get("id_client"),
        page=page,
        per_page=per_page
    )


def create_work_item_service(body: dict):

    if not body.get("work_number"):
        raise ValidationError("Work number wajib diisi.")

    if not body.get("work_name"):
        raise ValidationError("Nama pekerjaan wajib diisi.")

    if not body.get("work_type"):
        raise ValidationError("Work type wajib diisi.")

    if body["work_type"] not in ("TENDER", "MAINTENANCE"):
        raise ValidationError("Work type hanya boleh TENDER atau MAINTENANCE.")

    if not body.get("id_client"):
        raise ValidationError("Client wajib dipilih.")

    if body.get("progress_percent") is not None:
        try:
            progress_percent = float(body["progress_percent"])
        except (TypeError, ValueError):
            raise ValidationError("Progress harus berupa angka.")

        if progress_percent < 0 or progress_percent > 100:
            raise ValidationError("Progress harus berada antara 0 sampai 100.")

    if body.get("id_client_pic"):
        client_pic = get_client_pic_by_id(body["id_client_pic"])

        if not client_pic:
            raise NotFoundError("Client PIC tidak ditemukan.")

        if client_pic["id_client"] != body["id_client"]:
            raise ValidationError("Client PIC tidak sesuai dengan client.")

    client = get_client_by_id(body["id_client"])

    if not client:
        raise NotFoundError("Client tidak ditemukan.")

    duplicate = get_work_item_by_number(body["work_number"])

    if duplicate:
        raise ValidationError("Work number sudah digunakan.")

    return create_work_item(body)


def get_work_item_detail_service(id_work_item):

    work_item = get_work_item_detail(
        id_work_item
    )

    if not work_item:
        raise NotFoundError(
            "Work item tidak ditemukan."
        )

    return work_item


def update_work_item_service(id_work_item, body):

    current_work = get_work_item_by_id(id_work_item)

    if not current_work:
        raise NotFoundError("Work item tidak ditemukan.")

    if not body.get("work_number"):
        raise ValidationError("Work number wajib diisi.")

    if not body.get("work_name"):
        raise ValidationError("Nama pekerjaan wajib diisi.")

    if not body.get("work_type"):
        raise ValidationError("Work type wajib diisi.")

    if body["work_type"] not in (
        "TENDER",
        "MAINTENANCE"
    ):
        raise ValidationError("Work type hanya boleh TENDER atau MAINTENANCE.")

    if not body.get("id_client"):
        raise ValidationError("Client wajib dipilih.")

    # ---------------------------------------------------------------------- #
    # Check client
    # ---------------------------------------------------------------------- #

    client = get_client_by_id(body["id_client"])

    if not client:
        raise NotFoundError("Client tidak ditemukan.")

    # ---------------------------------------------------------------------- #
    # Check client PIC
    # ---------------------------------------------------------------------- #

    if body.get("id_client_pic"):

        client_pic = get_client_pic_by_id(body["id_client_pic"])

        if not client_pic:
            raise NotFoundError("Client PIC tidak ditemukan.")

        if client_pic["id_client"] != body["id_client"]:
            raise ValidationError("Client PIC tidak sesuai dengan client.")

    # ---------------------------------------------------------------------- #
    # Check duplicate work number
    # ---------------------------------------------------------------------- #

    duplicate = get_work_item_by_number(body["work_number"])

    if (duplicate and duplicate["id_work_item"] != id_work_item):
        raise ValidationError("Work number sudah digunakan.")

    # ---------------------------------------------------------------------- #
    # Update
    # ---------------------------------------------------------------------- #

    update_work_item(id_work_item, body)


def delete_work_item_service(id_work_item, updated_by):

    work_item = get_work_item_by_id(
        id_work_item
    )

    if not work_item:
        raise NotFoundError(
            "Work item tidak ditemukan."
        )

    delete_work_item(
        id_work_item,
        updated_by
    )


def get_work_item_options_service(context=None):

    return get_work_item_options(
        context=context
    )


def update_work_progress_service(id_work_item, data, updated_by):
    
    work_item = get_work_item_by_id(id_work_item)

    if not work_item:
        raise NotFoundError("Work Item tidak ditemukan")

    progress_percent = data.get("progress_percent")

    if progress_percent is None:
        raise ValidationError("Progress pekerjaan wajib diisi")

    try:
        progress_percent = float(progress_percent)
    except (TypeError, ValueError):
        raise ValidationError("Progress pekerjaan harus berupa angka")

    if progress_percent < 0 or progress_percent > 100:
        raise ValidationError("Progress pekerjaan harus berada di antara 0 sampai 100")

    progress_date = data.get("progress_date")
    notes = data.get("notes")

    return update_work_progress(
        id_work_item=id_work_item,
        progress_percent=progress_percent,
        progress_date=progress_date,
        notes=notes,
        updated_by=updated_by
    )


def close_work_item_service(id_work_item, updated_by):
    return close_work_item(
        id_work_item=id_work_item,
        updated_by=updated_by
    )