from api.shared.exceptions import ValidationError, NotFoundError
from .query import *


# ============================================================================ #
#                              #SECTION - CONTRACT                             #
# ============================================================================ #

def get_contract_list_service(filters):

    page = filters.get("page", 1)
    per_page = filters.get("per_page", 10)

    if page < 1:
        raise ValidationError("Page harus lebih besar dari 0")

    if per_page < 1:
        raise ValidationError("Per page harus lebih besar dari 0")

    return get_contract_list(filters)


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

    work_item = get_work_item_by_id(id_work_item)

    if not work_item:
        raise NotFoundError("Work Item tidak ditemukan")

    duplicate = get_contract_by_number(contract_number)

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

    if not id_contract:
        raise ValidationError("ID kontrak wajib diisi")

    contract = get_contract_by_id(id_contract)

    if not contract:
        raise NotFoundError("Kontrak tidak ditemukan")

    delete_contract(
        id_contract=id_contract,
        updated_by=updated_by
    )