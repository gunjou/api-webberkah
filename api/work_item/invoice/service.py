
from api.shared.exceptions import ValidationError, NotFoundError
from api.work_item.helper import upload_work_item_document, validate_rupiah
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


def create_invoice_service(body, created_by, document=None):

    id_completion = body.get("id_completion")
    invoice_number = body.get("invoice_number")
    invoice_date = body.get("invoice_date")
    invoice_value = body.get("invoice_value")
    vat_rate = body.get("vat_rate")
    due_date = body.get("due_date")
    notes = body.get("notes")

    # ------------------------------ Validate Input ------------------------------ #

    if not id_completion:
        raise ValidationError("BA wajib dipilih")

    if not invoice_number or not invoice_number.strip():
        raise ValidationError("Nomor invoice wajib diisi")

    invoice_number = invoice_number.strip()

    if not invoice_date:
        raise ValidationError("Tanggal invoice wajib diisi")

    if invoice_value is None:
        raise ValidationError("Nilai invoice wajib diisi")

    invoice_value = validate_rupiah(invoice_value, "Nilai invoice")

    if invoice_value <= 0:
        raise ValidationError("Nilai invoice harus lebih besar dari 0")

    if vat_rate is not None and not 0 <= vat_rate <= 100:
        raise ValidationError("PPN harus berada di antara 0 sampai 100")

    if due_date and due_date < invoice_date:
        raise ValidationError(
            "Tanggal jatuh tempo tidak boleh lebih kecil "
            "dari tanggal invoice"
        )

    # ---------------------- Completion / BA → Work Item ------------------------- #

    completion = get_completion_by_id(id_completion)

    if not completion:
        raise NotFoundError("BA tidak ditemukan")

    id_work_item = completion["id_work_item"]

    work_item = get_work_item_by_id(id_work_item)

    if not work_item:
        raise NotFoundError("Work Item tidak ditemukan")

    # ------------------------------ Validate Stage ------------------------------ #

    if work_item.get("current_stage") not in ("BA", "INVOICE", "PAYMENT"):
        raise ValidationError(
            "Invoice hanya dapat dibuat ketika Work Item berada pada tahap BA, INVOICE, atau PAYMENT"
        )

    # ----------------------- Check Duplicate Invoice Number ---------------------- #

    duplicate = get_invoice_by_number(invoice_number)

    if duplicate:
        raise ValidationError("Nomor invoice sudah digunakan")

    # ---------------------------- Upload Document ------------------------------- #

    document_url = None

    if document:
        document_url = upload_work_item_document(
            document,
            "invoice"
        )

    # ------------------------------ Create Invoice ------------------------------ #

    return create_invoice(
        id_work_item=id_work_item,
        id_completion=id_completion,
        invoice_number=invoice_number,
        invoice_date=invoice_date,
        invoice_value=invoice_value,
        vat_rate=vat_rate,
        due_date=due_date,
        document_url=document_url,
        notes=notes.strip() if notes else None,
        created_by=created_by
    )


def get_invoice_detail_service(id_invoice):

    if not id_invoice:
        raise ValidationError("ID invoice wajib diisi")

    invoice = get_invoice_detail(id_invoice)

    if not invoice:
        raise NotFoundError("Invoice tidak ditemukan")

    return invoice


def update_invoice_service(id_invoice, body, updated_by, document=None):

    if not id_invoice:
        raise ValidationError("ID invoice wajib diisi")

    # --------------------------------- Ambil Invoice ----------------------------- #

    invoice = get_invoice_by_id(id_invoice)

    if not invoice:
        raise NotFoundError("Invoice tidak ditemukan")

    # Work Item mengikuti invoice yang tersimpan, tidak bisa dipindah
    id_work_item = invoice["id_work_item"]
    id_completion = body.get("id_completion") or invoice["id_completion"]
    invoice_number = body.get("invoice_number")
    invoice_date = body.get("invoice_date")
    invoice_value = body.get("invoice_value")
    vat_rate = body.get("vat_rate")
    due_date = body.get("due_date")
    notes = body.get("notes")

    # ------------------------------ Validasi Input ------------------------------ #

    if not invoice_number or not invoice_number.strip():
        raise ValidationError("Nomor invoice wajib diisi")

    if not invoice_date:
        raise ValidationError("Tanggal invoice wajib diisi")

    if invoice_value is None:
        raise ValidationError("Nilai invoice wajib diisi")

    invoice_value = validate_rupiah(invoice_value, "Nilai invoice")

    if invoice_value <= 0:
        raise ValidationError("Nilai invoice harus lebih besar dari 0")

    if vat_rate is not None and not 0 <= vat_rate <= 100:
        raise ValidationError("PPN harus berada di antara 0 sampai 100")

    if due_date and due_date < invoice_date:
        raise ValidationError(
            "Tanggal jatuh tempo tidak boleh lebih kecil "
            "dari tanggal invoice"
        )

    # ------------------------------ Check Work Item ----------------------------- #

    work_item = get_work_item_by_id(id_work_item)

    if not work_item:
        raise NotFoundError("Work Item tidak ditemukan")

    # -------------------------- Validate Completion / BA ------------------------- #

    if id_completion:

        completion = get_completion_by_id(id_completion)

        if not completion:
            raise NotFoundError("BA tidak ditemukan")

        if completion["id_work_item"] != id_work_item:
            raise ValidationError("BA tidak terkait dengan Work Item yang dipilih")

    # ----------------------- Check Duplicate Invoice Number ---------------------- #

    duplicate = get_invoice_by_number(
        invoice_number=invoice_number.strip(),
        exclude_id=id_invoice
    )

    if duplicate:
        raise ValidationError("Nomor invoice sudah digunakan")

    # ---------------------------- Upload Document ------------------------------- #

    document_url = None

    if document:
        document_url = upload_work_item_document(
            document,
            "invoice"
        )

    # ------------------------------ Update Invoice ------------------------------ #

    update_invoice(
        id_invoice=id_invoice,
        id_work_item=id_work_item,
        id_completion=id_completion,
        invoice_number=invoice_number.strip(),
        invoice_date=invoice_date,
        invoice_value=invoice_value,
        vat_rate=vat_rate,
        due_date=due_date,
        document_url=document_url,
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

    # Invoice yang sudah punya pembayaran tidak boleh dihapus (hapus pembayarannya dulu)
    if count_active_payment(id_invoice) > 0:
        raise ValidationError(
            "Invoice yang sudah memiliki pembayaran tidak dapat dihapus"
        )

    return delete_invoice(
        id_invoice=id_invoice,
        id_work_item=id_work_item,
        updated_by=updated_by
    )

def get_billing_summary_service(id_completion, exclude_id=None):

    if not id_completion:
        raise ValidationError("BA wajib dipilih")

    completion = get_completion_by_id(id_completion)

    if not completion:
        raise NotFoundError("BA tidak ditemukan")

    summary = get_billing_summary_by_work_item(completion["id_work_item"], exclude_id)

    return {
        "id_completion": id_completion,
        "id_work_item": completion["id_work_item"],
        **summary,
        # Sugesti untuk form; backend tetap memvalidasi ulang saat simpan
        "suggested_invoice_value": summary["remaining_value"],
        "suggested_vat_rate": summary["vat_rate"],
    }
