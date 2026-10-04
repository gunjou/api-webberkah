from api.shared.exceptions import ValidationError, NotFoundError
from .query import *


# ============================================================================ #
#                         #SECTION - QUOTATION                                 #
# ============================================================================ #

def get_quotation_list_service(filters: dict):

    page = filters.get("page", 1)
    per_page = filters.get("per_page", 10)

    if page < 1:
        raise ValidationError("Page harus lebih besar atau sama dengan 1.")

    if per_page < 1:
        raise ValidationError("Per page harus lebih besar atau sama dengan 1.")

    if per_page > 100:
        raise ValidationError("Per page maksimal 100.")

    return get_quotation_list(
        search=filters.get("search"),
        status=filters.get("status"),
        id_work_item=filters.get("id_work_item"),
        page=page,
        per_page=per_page
    )


def create_quotation_service(body: dict):

    if not body.get("id_work_item"):
        raise ValidationError("Work item wajib dipilih.")

    if not body.get("proposal_number"):
        raise ValidationError("Nomor penawaran wajib diisi.")

    if not body.get("proposal_date"):
        raise ValidationError("Tanggal penawaran wajib diisi.")

    # ---------------------------------------------------------------------- #
    # Check Work Item
    # ---------------------------------------------------------------------- #

    work_item = get_work_item_by_id(body["id_work_item"])

    if not work_item:
        raise NotFoundError("Work item tidak ditemukan.")

    # ---------------------------------------------------------------------- #
    # Check duplicate quotation number
    # ---------------------------------------------------------------------- #

    duplicate = get_quotation_by_number(body["proposal_number"])

    if duplicate:
        raise ValidationError("Nomor penawaran sudah digunakan.")

    # ---------------------------------------------------------------------- #
    # Validate proposal value
    # ---------------------------------------------------------------------- #

    if body.get("proposal_value") is not None:

        try:
            proposal_value = float(body["proposal_value"])
        except (TypeError, ValueError):
            raise ValidationError("Nilai penawaran harus berupa angka.")

        if proposal_value < 0:
            raise ValidationError("Nilai penawaran tidak boleh kurang dari 0.")

    # ---------------------------------------------------------------------- #
    # Validate status
    # ---------------------------------------------------------------------- #

    status = body.get("status") or "DRAFT"

    if status not in ("DRAFT", "SUBMITTED", "WON", "LOST", "EXPIRED", "CANCELLED"):
        raise ValidationError("Status penawaran tidak valid.")

    body["status"] = status

    return create_quotation(body)


def get_quotation_detail_service(id_proposal):

    if not id_proposal:
        raise ValidationError("ID penawaran wajib diisi")

    quotation = get_quotation_detail(id_proposal)

    if not quotation:
        raise NotFoundError("Penawaran tidak ditemukan")

    return quotation


def update_quotation_service(id_proposal, body, updated_by):

    if not id_proposal:
        raise ValidationError("ID penawaran wajib diisi")

    quotation = get_quotation_by_id(id_proposal)

    if not quotation:
        raise NotFoundError("Penawaran tidak ditemukan")

    id_work_item = body.get("id_work_item")

    if not id_work_item:
        raise ValidationError("Work Item wajib dipilih")

    proposal_number = body.get("proposal_number")

    if not proposal_number or not proposal_number.strip():
        raise ValidationError("Nomor penawaran wajib diisi")

    proposal_date = body.get("proposal_date")

    if not proposal_date:
        raise ValidationError("Tanggal penawaran wajib diisi")

    work_item = get_work_item_by_id(id_work_item)

    if not work_item:
        raise NotFoundError("Work Item tidak ditemukan")

    duplicate = get_quotation_by_number(
        proposal_number=proposal_number,
        exclude_id=id_proposal
    )

    if duplicate:
        raise ValidationError("Nomor penawaran sudah digunakan")

    proposal_value = body.get("proposal_value")

    if proposal_value is not None and proposal_value < 0:
        raise ValidationError("Nilai penawaran tidak boleh kurang dari 0")

    status = body.get("status", "DRAFT")

    allowed_status = ["DRAFT", "SUBMITTED", "WON", "LOST", "EXPIRED", "CANCELLED"]

    if status not in allowed_status:
        raise ValidationError("Status penawaran tidak valid")

    return update_quotation(
        id_proposal=id_proposal,
        id_work_item=id_work_item,
        proposal_number=proposal_number.strip(),
        proposal_date=proposal_date,
        proposal_value=proposal_value,
        valid_until=body.get("valid_until"),
        status=status,
        notes=body.get("notes"),
        updated_by=updated_by
    )


def delete_quotation_service(id_proposal, updated_by):

    if not id_proposal:
        raise ValidationError("ID penawaran wajib diisi")

    quotation = get_quotation_by_id(id_proposal)

    if not quotation:
        raise NotFoundError("Penawaran tidak ditemukan")

    delete_quotation(
        id_proposal=id_proposal,
        updated_by=updated_by
    )