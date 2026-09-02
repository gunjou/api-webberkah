from decimal import Decimal

from api.shared.exceptions import ValidationError, NotFoundError
from api.shared.helper import get_wita
from api.utils.config import engine
from api.utils.pdf_helper import _format_filename_date, _safe_filename

from .query import *
from .pdf import generate_purchase_request_pdf_with_attachment


# ============================================================================ #
#                   #SECTION - CREATE PURCHASE REQUEST                        #
# ============================================================================ #

# ===================== #ANCHOR - CREATE PURCHASE REQUEST =================== #

def create_purchase_request_service(body: dict):

    items = body.get("items", [])

    if not items:
        raise ValidationError("Minimal harus terdapat 1 item pengajuan.")

    if body.get("priority") not in ("NORMAL", "URGENT", "TOP_URGENT"):
        raise ValidationError("Priority tidak valid.")

    total_amount = Decimal("0")

    for index, item in enumerate(items, start=1):

        if not item.get("keterangan"):
            raise ValidationError(f"Keterangan item ke-{index} wajib diisi.")

        if not item.get("unit"):
            raise ValidationError(f"Unit item ke-{index} wajib diisi.")

        if item.get("harga_satuan") is None:
            raise ValidationError(f"Harga satuan item ke-{index} wajib diisi.")

        if item.get("jumlah") is None:
            raise ValidationError(f"Jumlah item ke-{index} wajib diisi.")

        harga_satuan = Decimal(str(item["harga_satuan"]))
        jumlah = Decimal(str(item["jumlah"]))

        if harga_satuan < 0:
            raise ValidationError(
                f"Harga satuan item ke-{index} tidak boleh negatif."
            )

        if jumlah <= 0:
            raise ValidationError(
                f"Jumlah item ke-{index} harus lebih besar dari 0."
            )

        item["item_no"] = index
        item["total"] = harga_satuan * jumlah

        total_amount += item["total"]

    body["total_amount"] = total_amount
    body["status"] = "REQUESTED"
    body["is_active"] = 1

    with engine.begin() as conn:

        pegawai = get_active_pegawai(
            conn=conn,
            id_pegawai=body["id_pegawai"]
        )

        if not pegawai:
            raise NotFoundError("Pegawai tidak ditemukan atau tidak aktif.")

        departemen = get_active_departemen(
            conn=conn,
            id_departemen=body["id_departemen"]
        )

        if not departemen:
            raise NotFoundError("Departemen tidak ditemukan atau tidak aktif.")

        now = get_wita()

        body["request_number"] = generate_request_number(conn)
        body["created_at"] = now
        body["updated_at"] = now

        id_request = create_purchase_request(
            conn=conn,
            body=body
        )

        create_purchase_request_items(
            conn=conn,
            id_request=id_request,
            items=items,
            now=now
        )

        create_purchase_request_history(
            conn=conn,
            id_request=id_request,
            status="REQUESTED",
            nama_pegawai=pegawai["nama_lengkap"],
            note=body.get("note"),
            now=now
        )

    return {
        "id_request": id_request,
        "request_number": body["request_number"],
        "status": "REQUESTED",
        "total_amount": total_amount
    }

# ================ #!SECTION - CREATE PURCHASE REQUEST ====================== #


# ======================= #ANCHOR - LIST PURCHASE REQUEST ==================== #

def get_purchase_request_list_service(id_user: int, account_type: str, filters: dict):

    status = filters.get("status")

    valid_statuses = (
        "ACTIVE",
        "REQUESTED",
        "REVIEWED",
        "APPROVED",
        "REJECTED",
        "PAID"
    )

    if status and status not in valid_statuses:
        raise ValidationError(
            "Status purchase request tidak valid."
        )

    if account_type not in ("admin", "pegawai"):
        raise ValidationError(
            "Account type tidak valid."
        )

    tanggal_mulai = filters.get("tanggal_mulai")
    tanggal_selesai = filters.get("tanggal_selesai")

    if tanggal_mulai and tanggal_selesai:
        if tanggal_mulai > tanggal_selesai:
            raise ValidationError(
                "Tanggal mulai tidak boleh lebih besar "
                "dari tanggal selesai."
            )

    return get_purchase_request_list(
        id_user=id_user,
        account_type=account_type,
        filters=filters
    )

# =========================== #ANCHOR - DATA HISTORY ========================= #

def get_purchase_request_data_history_service(id_user: int, account_type: str, filters: dict):

    status = filters.get("status") or "PAID"

    if status not in ("PAID", "REJECTED"):
        raise ValidationError(
            "Status history purchase request tidak valid."
        )

    if account_type not in ("admin", "pegawai"):
        raise ValidationError(
            "Account type tidak valid."
        )

    page = filters.get("page", 1)
    limit = filters.get("limit", 10)

    if page < 1:
        raise ValidationError(
            "Page harus lebih besar atau sama dengan 1."
        )

    if limit < 1 or limit > 100:
        raise ValidationError(
            "Limit harus berada antara 1 sampai 100."
        )

    tanggal_mulai = filters.get("tanggal_mulai")
    tanggal_selesai = filters.get("tanggal_selesai")

    if tanggal_mulai and tanggal_selesai:
        if tanggal_mulai > tanggal_selesai:
            raise ValidationError(
                "Tanggal mulai tidak boleh lebih besar "
                "dari tanggal selesai."
            )

    return get_purchase_request_data_history(
        id_user=id_user,
        account_type=account_type,
        filters=filters
    )
    


# ============================================================================ #
#                    #SECTION - DETAIL PURCHASE REQUEST                       #
# ============================================================================ #

# ======================= #ANCHOR - DETAIL REQUEST =========================== #

def get_purchase_request_detail_service(id_request: int, account_type: str, id_pegawai: int = None):
    
    purchase_request = get_purchase_request_detail(
        id_request=id_request,
        account_type=account_type,
        id_pegawai=id_pegawai
    )

    if not purchase_request:
        raise NotFoundError("Purchase request tidak ditemukan.")

    return purchase_request


# ======================= #ANCHOR - UPDATE REQUEST ============================ #

def update_purchase_request_service(id_request: int, id_pegawai: int, body: dict):

    request_data = get_purchase_request_for_update(
        id_request=id_request,
        id_pegawai=id_pegawai
    )

    if not request_data:
        raise NotFoundError("Pengajuan tidak ditemukan.")

    status = request_data["status"]

    if status not in ("REQUESTED", "REJECTED"):
        raise ValidationError(
            f"Pengajuan dengan status {status} tidak dapat diedit."
        )

    # ------------------------------------------------------------------------ #
    # VALIDASI DEPARTEMEN
    # ------------------------------------------------------------------------ #

    if body.get("id_departemen") is not None:

        department = get_active_department(
            body["id_departemen"]
        )

        if not department:
            raise ValidationError(
                "Departemen tidak ditemukan atau tidak aktif."
            )

    # ------------------------------------------------------------------------ #
    # VALIDASI PRIORITY
    # ------------------------------------------------------------------------ #

    if body.get("priority") is not None:

        if body["priority"] not in (
            "NORMAL",
            "URGENT",
            "TOP_URGENT"
        ):
            raise ValidationError(
                "Priority tidak valid."
            )

    # ------------------------------------------------------------------------ #
    # VALIDASI ITEMS
    # ------------------------------------------------------------------------ #

    items = body.get("items")

    if items is not None:

        if not isinstance(items, list) or not items:
            raise ValidationError(
                "Items pengajuan wajib diisi minimal satu item."
            )

        total_amount = Decimal("0")
        normalized_items = []

        for index, item in enumerate(items, start=1):

            if not item.get("keterangan"):
                raise ValidationError(
                    f"Keterangan item ke-{index} wajib diisi."
                )

            if not item.get("unit"):
                raise ValidationError(
                    f"Unit item ke-{index} wajib diisi."
                )

            if item.get("harga_satuan") is None:
                raise ValidationError(
                    f"Harga satuan item ke-{index} wajib diisi."
                )

            if item.get("jumlah") is None:
                raise ValidationError(
                    f"Jumlah item ke-{index} wajib diisi."
                )

            harga_satuan = Decimal(
                str(item["harga_satuan"])
            )

            jumlah = Decimal(
                str(item["jumlah"])
            )

            if harga_satuan < 0:
                raise ValidationError(
                    f"Harga satuan item ke-{index} tidak boleh negatif."
                )

            if jumlah <= 0:
                raise ValidationError(
                    f"Jumlah item ke-{index} harus lebih besar dari 0."
                )

            item_total = harga_satuan * jumlah
            total_amount += item_total

            normalized_items.append({
                "item_no": index,
                "keterangan": item["keterangan"],
                "unit": item["unit"],
                "harga_satuan": harga_satuan,
                "jumlah": jumlah,
                "total": item_total
            })

        items = normalized_items

    # ------------------------------------------------------------------------ #
    # TRANSACTION
    # ------------------------------------------------------------------------ #

    now = get_wita()

    with engine.begin() as conn:

        update_purchase_request(
            conn=conn,
            id_request=id_request,
            body=body,
            total_amount=total_amount if items is not None else None,
            now=now
        )

        if items is not None:

            delete_purchase_request_items(
                conn=conn,
                id_request=id_request
            )

            create_purchase_request_items(
                conn=conn,
                id_request=id_request,
                items=items,
                now=now
            )

        # -------------------------------------------------------------------- #
        # REJECTED -> REQUESTED
        # -------------------------------------------------------------------- #

        if status == "REJECTED":

            update_purchase_request_status(
                conn=conn,
                id_request=id_request,
                status="REQUESTED",
                now=now
            )

            create_purchase_request_history(
                conn=conn,
                id_request=id_request,
                status="REQUESTED",
                nama_pegawai=request_data["nama_pegawai"],
                note=body.get("note"),
                now=now
            )


# ======================= #ANCHOR - DELETE REQUEST ============================ #

def delete_purchase_request_service(id_request: int, id_pegawai: int, is_admin: bool):

    with engine.begin() as conn:

        request_data = get_purchase_request_for_delete(
            conn=conn,
            id_request=id_request,
            id_pegawai=None if is_admin else id_pegawai
        )

        if not request_data:
            raise NotFoundError(
                "Pengajuan tidak ditemukan."
            )

        if request_data["status"] == "PAID":
            raise ValidationError(
                "Pengajuan yang sudah PAID tidak dapat dihapus."
            )

        update_purchase_request_inactive(
            conn=conn,
            id_request=id_request
        )

# ==================== #!SECTION - DETAIL PURCHASE REQUEST =================== #



# ============================================================================ #
#                            #SECTION - STATUS UPDATE                          #
# ============================================================================ #

# ======================== #ANCHOR - REVIEW REQUEST =========================== #

def review_purchase_request_service(id_request: int, nama_pegawai: str, note: str = None):

    with engine.begin() as conn:

        request_data = get_purchase_request_for_status_update(
            conn=conn,
            id_request=id_request
        )

        if not request_data:
            raise NotFoundError(
                "Pengajuan tidak ditemukan."
            )

        if request_data["status"] != "REQUESTED":
            raise ValidationError(
                f"Pengajuan dengan status {request_data['status']} tidak dapat direview."
            )

        now = get_wita()

        update_purchase_request_status(
            conn=conn,
            id_request=id_request,
            status="REVIEWED",
            now=now
        )

        create_purchase_request_history(
            conn=conn,
            id_request=id_request,
            status="REVIEWED",
            nama_pegawai=nama_pegawai,
            note=note,
            now=now
        )


# ======================= #ANCHOR - APPROVE REQUEST =========================== #

def approve_purchase_request_service(id_request: int, nama_pegawai: str, note: str = None):

    with engine.begin() as conn:

        request_data = get_purchase_request_for_status_update(
            conn=conn,
            id_request=id_request
        )

        if not request_data:
            raise NotFoundError(
                "Pengajuan tidak ditemukan."
            )

        if request_data["status"] != "REVIEWED":
            raise ValidationError(
                f"Pengajuan dengan status {request_data['status']} tidak dapat diapprove."
            )

        now = get_wita()

        update_purchase_request_status(
            conn=conn,
            id_request=id_request,
            status="APPROVED",
            now=now
        )

        create_purchase_request_history(
            conn=conn,
            id_request=id_request,
            status="APPROVED",
            nama_pegawai=nama_pegawai,
            note=note,
            now=now
        )


# ======================== #ANCHOR - REJECT REQUEST =========================== #

def reject_purchase_request_service(id_request: int, nama_pegawai: str, note: str):

    with engine.begin() as conn:

        request_data = get_purchase_request_for_status_update(
            conn=conn,
            id_request=id_request
        )

        if not request_data:
            raise NotFoundError(
                "Pengajuan tidak ditemukan."
            )

        if request_data["status"] not in ("REQUESTED", "REVIEWED"):
            raise ValidationError(
                f"Pengajuan dengan status {request_data['status']} tidak dapat direject."
            )

        now = get_wita()

        update_purchase_request_status(
            conn=conn,
            id_request=id_request,
            status="REJECTED",
            now=now
        )

        create_purchase_request_history(
            conn=conn,
            id_request=id_request,
            status="REJECTED",
            nama_pegawai=nama_pegawai,
            note=note,
            now=now
        )


# ========================= #ANCHOR - PAID REQUEST ============================ #

def mark_purchase_request_paid_service(id_request: int, nama_pegawai: str, note: str = None):

    with engine.begin() as conn:

        request_data = get_purchase_request_for_status_update(
            conn=conn,
            id_request=id_request
        )

        if not request_data:
            raise NotFoundError(
                "Pengajuan tidak ditemukan."
            )

        if request_data["status"] != "APPROVED":
            raise ValidationError(
                f"Pengajuan dengan status {request_data['status']} tidak dapat ditandai sebagai paid."
            )

        now = get_wita()

        update_purchase_request_status(
            conn=conn,
            id_request=id_request,
            status="PAID",
            now=now
        )

        create_purchase_request_history(
            conn=conn,
            id_request=id_request,
            status="PAID",
            nama_pegawai=nama_pegawai,
            note=note,
            now=now
        )

# ========================= #!SECTION - STATUS UPDATE ======================== #



# ============================================================================ #
#                    #SECTION - PURCHASE REQUEST HISTORY                       #
# ============================================================================ #

# ======================= #ANCHOR - GET REQUEST HISTORY ====================== #

def get_purchase_request_history_service(id_request: int, id_pegawai: int = None, is_admin: bool = False):

    request_data = get_purchase_request_owner(
        id_request=id_request
    )

    if not request_data:
        raise NotFoundError(
            "Pengajuan tidak ditemukan."
        )

    if not is_admin and request_data["id_pegawai"] != id_pegawai:
        raise ValidationError(
            "Anda tidak memiliki akses ke pengajuan ini."
        )

    return get_purchase_request_history(
        id_request=id_request
    )

# ================== #!SECTION - PURCHASE REQUEST HISTORY ==================== #



# ============================================================================ #
#                     #SECTION - USER DASHBOARD                                #
# ============================================================================ #

# ======================= #ANCHOR - MY SUMMARY =============================== #

def get_my_purchase_request_summary_service(id_pegawai: int):
    summary = get_purchase_request_dashboard_summary(
        id_pegawai=id_pegawai
    )

    requests = get_purchase_request_dashboard_list(
        id_pegawai=id_pegawai
    )

    return {
        "summary": summary,
        "requests": requests
    }

# ==================== #!SECTION - USER DASHBOARD ============================ #



# ============================================================================ #
#                       #SECTION - EXPORT PURCHASE REQUEST                     #
# ============================================================================ #

# ===================== #ANCHOR - DOWNLOAD PURCHASE REQUEST =================== #

def generate_purchase_request_pdf_service(
    id_request: int,
    id_pegawai: int = None
):
    """
    Generate Purchase Request PDF beserta attachment.

    Access:
    - Admin    : dapat melihat semua purchase request
    - Pegawai  : hanya dapat melihat purchase request miliknya
    """

    # =================================================
    # 1. GET PURCHASE REQUEST
    # =================================================

    purchase_request = get_purchase_request_pdf(
        id_request=id_request,
        id_pegawai=id_pegawai
    )

    if not purchase_request:
        raise NotFoundError(
            "Purchase request tidak ditemukan."
        )

    # =================================================
    # 2. GET ITEMS
    # =================================================

    items = get_purchase_request_pdf_items(
        id_request=id_request
    )

    # =================================================
    # 3. GET HISTORY
    # =================================================

    history = get_purchase_request_pdf_history(
        id_request=id_request
    )

    # =================================================
    # 4. GENERATE PDF
    # =================================================

    pdf = generate_purchase_request_pdf_with_attachment(
        purchase_request=purchase_request,
        items=items,
        history=history
    )

    # =================================================
    # 5. PREPARE FILENAME
    # =================================================

    nama_pegawai = _safe_filename(
        purchase_request.get("nama_pegawai")
    )

    nama_pekerjaan = _safe_filename(
        purchase_request.get("nama_pekerjaan")
    )

    tanggal_request = _format_filename_date(
        purchase_request.get("tanggal_request")
    )

    filename = (
        f"Pengajuan {nama_pegawai} - "
        f"{nama_pekerjaan} - "
        f"{tanggal_request}.pdf"
    )

    # =================================================
    # 6. RETURN
    # =================================================

    return {
        "pdf": pdf,
        "filename": filename
    }


# ================= #!SECTION - DOWNLOAD PURCHASE REQUEST ====================== #