from api.shared.exceptions import ValidationError, NotFoundError
from .query import *


# ============================================================================ #
#                              #SECTION - CONTRACT                             #
# ============================================================================ #

def get_contract_list_service(filters):

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

    return get_contract_list(
        stage=stage,
        search=filters.get("search"),
        status=filters.get("status"),
        id_work_item=filters.get("id_work_item"),
        id_client=filters.get("id_client"),
        page=page,
        per_page=per_page
    )


def create_contract_service(body, created_by):

    id_work_item = body.get("id_work_item")

    if not id_work_item:
        raise ValidationError("Work Item wajib dipilih")

    contract_number = body.get("contract_number")

    if not contract_number or not contract_number.strip():
        raise ValidationError("Nomor kontrak wajib diisi")

    contract_date = body.get("contract_date")

    if not contract_date:
        raise ValidationError("Tanggal kontrak wajib diisi")

    # ---------------------------------------------------------------------- #
    # Check Work Item
    # ---------------------------------------------------------------------- #

    work_item = get_work_item_by_id(id_work_item)

    if not work_item:
        raise NotFoundError("Work Item tidak ditemukan")

    # ---------------------------------------------------------------------- #
    # Validate Stage
    # ---------------------------------------------------------------------- #

    current_stage = work_item["current_stage"]
    work_type = work_item["work_type"]

    if work_type == "TENDER":

        if current_stage != "QUOTATION":
            raise ValidationError(
                "Kontrak untuk work type TENDER hanya dapat dibuat "
                "ketika work item berada pada stage QUOTATION."
            )

    elif work_type == "MAINTENANCE":

        if current_stage not in ("IDENTIFIED", "QUOTATION"):
            raise ValidationError(
                "Kontrak untuk work type MAINTENANCE hanya dapat dibuat "
                "ketika work item berada pada stage IDENTIFIED atau QUOTATION."
            )

    # ---------------------------------------------------------------------- #
    # Check Duplicate Contract Number
    # ---------------------------------------------------------------------- #

    duplicate = get_contract_by_number(contract_number)

    if duplicate:
        raise ValidationError("Nomor kontrak sudah digunakan")

    # ---------------------------------------------------------------------- #
    # Validate Contract Date
    # ---------------------------------------------------------------------- #

    start_date = body.get("start_date")
    end_date = body.get("end_date")

    if start_date and end_date and end_date < start_date:
        raise ValidationError("Tanggal selesai kontrak tidak boleh lebih kecil dari tanggal mulai")

    # ---------------------------------------------------------------------- #
    # Validate Contract Value
    # ---------------------------------------------------------------------- #

    contract_value = body.get("contract_value")

    if contract_value is not None:

        try:
            contract_value = float(contract_value)
        except (TypeError, ValueError):
            raise ValidationError("Nilai kontrak harus berupa angka")

        if contract_value < 0:
            raise ValidationError("Nilai kontrak tidak boleh kurang dari 0")

    # ---------------------------------------------------------------------- #
    # Validate VAT Rate
    # ---------------------------------------------------------------------- #

    vat_rate = body.get("vat_rate")

    if vat_rate is not None:

        try:
            vat_rate = float(vat_rate)
        except (TypeError, ValueError):
            raise ValidationError("VAT rate harus berupa angka")

        if vat_rate < 0 or vat_rate > 100:
            raise ValidationError("VAT rate harus berada antara 0 sampai 100")

    # ---------------------------------------------------------------------- #
    # Validate Status
    # ---------------------------------------------------------------------- #

    status = body.get("status", "ACTIVE")

    allowed_status = ["ACTIVE", "COMPLETED", "CANCELLED"]

    if status not in allowed_status:
        raise ValidationError("Status kontrak tidak valid")

    # ---------------------------------------------------------------------- #
    # Create Contract
    # ---------------------------------------------------------------------- #

    return create_contract(
        id_work_item=id_work_item,
        contract_number=contract_number.strip(),
        contract_date=contract_date,
        start_date=start_date,
        end_date=end_date,
        contract_value=contract_value,
        vat_rate=vat_rate,
        status=status,
        notes=body.get("notes"),
        created_by=created_by
    )


def get_contract_detail_service(id_contract):

    if not id_contract:
        raise ValidationError("ID kontrak wajib diisi")

    contract = get_contract_detail(id_contract)

    if not contract:
        raise NotFoundError("Kontrak tidak ditemukan")

    return contract


def update_contract_service(id_contract, body, updated_by):

    if not id_contract:
        raise ValidationError("ID kontrak wajib diisi")

    contract = get_contract_by_id(id_contract)

    if not contract:
        raise NotFoundError("Kontrak tidak ditemukan")

    id_work_item = body.get("id_work_item")

    if not id_work_item:
        raise ValidationError("Work Item wajib dipilih")

    contract_number = body.get("contract_number")

    if not contract_number or not contract_number.strip():
        raise ValidationError("Nomor kontrak wajib diisi")

    contract_date = body.get("contract_date")

    if not contract_date:
        raise ValidationError("Tanggal kontrak wajib diisi")

    work_item = get_work_item_by_id(id_work_item)

    if not work_item:
        raise NotFoundError("Work Item tidak ditemukan")

    duplicate = get_contract_by_number(
        contract_number=contract_number,
        exclude_id=id_contract
    )

    if duplicate:
        raise ValidationError("Nomor kontrak sudah digunakan")

    start_date = body.get("start_date")
    end_date = body.get("end_date")

    if start_date and end_date and end_date < start_date:
        raise ValidationError("Tanggal selesai kontrak tidak boleh lebih kecil dari tanggal mulai")

    contract_value = body.get("contract_value")

    if contract_value is not None and contract_value < 0:
        raise ValidationError("Nilai kontrak tidak boleh kurang dari 0")

    vat_rate = body.get("vat_rate")

    if vat_rate is not None and (vat_rate < 0 or vat_rate > 100):
        raise ValidationError("VAT rate harus berada antara 0 sampai 100")

    status = body.get("status", "ACTIVE")

    allowed_status = ["ACTIVE", "COMPLETED", "CANCELLED"]

    if status not in allowed_status:
        raise ValidationError("Status kontrak tidak valid")

    return update_contract(
        id_contract=id_contract,
        id_work_item=id_work_item,
        contract_number=contract_number.strip(),
        contract_date=contract_date,
        start_date=start_date,
        end_date=end_date,
        contract_value=contract_value,
        vat_rate=vat_rate,
        status=status,
        notes=body.get("notes"),
        updated_by=updated_by
    )


def delete_contract_service(id_contract, updated_by):
    
    contract = get_contract_by_id(id_contract)

    if not contract:
        raise NotFoundError("Kontrak tidak ditemukan.")

    if contract.get("is_active") != 1:
        raise ValidationError("Kontrak sudah tidak aktif.")

    id_work_item = contract.get("id_work_item")

    work_item = get_work_item_by_id(id_work_item)

    if not work_item:
        raise NotFoundError("Work Item tidak ditemukan.")

    current_stage = work_item.get("current_stage")

    # Contract hanya boleh dihapus ketika Work Item masih berada
    # pada stage CONTRACT.
    if current_stage != "CONTRACT":
        raise ValidationError("Kontrak hanya dapat dihapus ketika Work Item berada pada tahap CONTRACT.")

    return delete_contract(
        id_contract=id_contract,
        id_work_item=id_work_item,
        updated_by=updated_by
    )
