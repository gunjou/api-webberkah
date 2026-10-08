
from api.shared.exceptions import ValidationError, NotFoundError
from .query import *


# ============================================================================ #
#                               #SECTION - INVOICE                             #
# ============================================================================ #

def get_invoice_list_service(filters):

    stage = filters.get("stage", "ACTIVE")
    page = filters.get("page")
    per_page = filters.get("per_page")

    # ============================ VALIDATE PAGINATION =========================== #

    if page is not None and page < 1:
        raise ValidationError("Page harus lebih besar dari 0")

    if per_page is not None and per_page < 1:
        raise ValidationError("Per Page harus lebih besar dari 0")

    # ======================= PAGINATION HANYA UNTUK CLOSED ====================== #

    if stage == "ACTIVE":
        page = None
        per_page = None

    return get_invoice_list(
        stage=stage,
        health_status=filters.get("health_status"),
        id_client=filters.get("id_client"),
        payment_status=filters.get("payment_status"),
        search=filters.get("search"),
        page=page,
        per_page=per_page
    )


def create_invoice_service(data, created_by):

    id_work_item = data.get("id_work_item")
    id_completion = data.get("id_completion")
    invoice_number = data.get("invoice_number")
    invoice_date = data.get("invoice_date")
    invoice_value = data.get("invoice_value")
    vat_rate = data.get("vat_rate")
    due_date = data.get("due_date")
    document_url = data.get("document_url")
    notes = data.get("notes")

    # VALIDATION
    if not id_work_item:
        raise ValidationError("Work Item wajib dipilih")

    if not id_completion:
        raise ValidationError("BA wajib dipilih")

    if not invoice_number or not invoice_number.strip():
        raise ValidationError("Nomor invoice wajib diisi")

    invoice_number = invoice_number.strip()

    if not invoice_date:
        raise ValidationError("Tanggal invoice wajib diisi")

    if invoice_value is None:
        raise ValidationError("Nilai invoice wajib diisi")

    if invoice_value < 0:
        raise ValidationError("Nilai invoice tidak boleh kurang dari 0")

    if vat_rate is not None and not 0 <= vat_rate <= 100:
        raise ValidationError("PPN harus berada di antara 0 sampai 100")

    if due_date and due_date < invoice_date:
        raise ValidationError(
            "Tanggal jatuh tempo tidak boleh lebih kecil "
            "dari tanggal invoice"
        )

    # VALIDATE WORK ITEM
    work_item = get_work_item_by_id(id_work_item)

    if not work_item:
        raise NotFoundError("Work Item tidak ditemukan")

    # Invoice hanya dapat dibuat ketika Work Item
    # berada pada stage BA
    if work_item.get("current_stage") != "BA":
        raise ValidationError("Invoice hanya dapat dibuat ketika Work Item berada pada tahap BA")

    # VALIDATE COMPLETION / BA
    completion = get_completion_by_id(id_completion)

    if not completion:
        raise NotFoundError("BA tidak ditemukan")

    if completion["id_work_item"] != id_work_item:
        raise ValidationError("BA tidak terkait dengan Work Item yang dipilih")

    # VALIDATE DUPLICATE INVOICE
    duplicate = get_invoice_by_number(invoice_number)

    if duplicate:
        raise ValidationError("Nomor invoice sudah digunakan")

    # CREATE
    return create_invoice(
        id_work_item=id_work_item,
        id_completion=id_completion,
        invoice_number=invoice_number,
        invoice_date=invoice_date,
        invoice_value=invoice_value,
        vat_rate=vat_rate,
        due_date=due_date,
        document_url=document_url.strip()
        if document_url else None,
        notes=notes.strip()
        if notes else None,
        created_by=created_by
    )


def get_invoice_detail_service(id_invoice):

    if not id_invoice:
        raise ValidationError("ID invoice wajib diisi")

    invoice = get_invoice_detail(id_invoice)

    if not invoice:
        raise NotFoundError("Invoice tidak ditemukan")

    return invoice


def update_invoice_service(id_invoice, data, updated_by):

    if not id_invoice:
        raise ValidationError("ID invoice wajib diisi")

    invoice = get_invoice_by_id(id_invoice)

    if not invoice:
        raise NotFoundError("Invoice tidak ditemukan")

    id_work_item = data.get("id_work_item")
    id_completion = data.get("id_completion")
    invoice_number = data.get("invoice_number")
    invoice_date = data.get("invoice_date")
    invoice_value = data.get("invoice_value")
    vat_rate = data.get("vat_rate")
    due_date = data.get("due_date")
    document_url = data.get("document_url")
    notes = data.get("notes")

    if not id_work_item:
        raise ValidationError("Work Item wajib dipilih")

    if not invoice_number or not invoice_number.strip():
        raise ValidationError("Nomor invoice wajib diisi")

    if not invoice_date:
        raise ValidationError("Tanggal invoice wajib diisi")

    if invoice_value is None:
        raise ValidationError("Nilai invoice wajib diisi")

    if invoice_value < 0:
        raise ValidationError("Nilai invoice tidak boleh kurang dari 0")

    if vat_rate is not None and not 0 <= vat_rate <= 100:
        raise ValidationError("PPN harus berada di antara 0 sampai 100")

    if due_date and due_date < invoice_date:
        raise ValidationError("Tanggal jatuh tempo tidak boleh lebih kecil dari tanggal invoice")

    work_item = get_work_item_by_id(id_work_item)

    if not work_item:
        raise NotFoundError("Work Item tidak ditemukan")

    if id_completion:

        completion = get_completion_by_id(id_completion)

        if not completion:
            raise NotFoundError("BA tidak ditemukan")

        if completion["id_work_item"] != id_work_item:
            raise ValidationError("BA tidak terkait dengan Work Item yang dipilih")

    duplicate = get_invoice_by_number(
        invoice_number=invoice_number.strip(),
        exclude_id=id_invoice
    )

    if duplicate:
        raise ValidationError("Nomor invoice sudah digunakan")

    update_invoice(
        id_invoice=id_invoice,
        id_work_item=id_work_item,
        id_completion=id_completion,
        invoice_number=invoice_number.strip(),
        invoice_date=invoice_date,
        invoice_value=invoice_value,
        vat_rate=vat_rate,
        due_date=due_date,
        document_url=document_url.strip() if document_url else None,
        notes=notes.strip() if notes else None,
        updated_by=updated_by
    )

    return get_invoice_detail(id_invoice)


def delete_invoice_service(id_invoice, updated_by):

    if not id_invoice:
        raise ValidationError("ID invoice wajib diisi")

    invoice = get_invoice_by_id(id_invoice)

    if not invoice:
        raise NotFoundError("Invoice tidak ditemukan")

    id_work_item = invoice.get("id_work_item")

    work_item = get_work_item_by_id(id_work_item)

    if not work_item:
        raise NotFoundError("Work Item tidak ditemukan")

    # Invoice hanya boleh dihapus ketika
    # Work Item masih berada pada stage INVOICE
    if work_item.get("current_stage") != "INVOICE":
        raise ValidationError(
            "Invoice hanya dapat dihapus ketika Work Item berada pada tahap INVOICE"
        )

    return delete_invoice(
        id_invoice=id_invoice,
        id_work_item=id_work_item,
        updated_by=updated_by
    )