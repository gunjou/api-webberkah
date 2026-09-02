from sqlalchemy import text

from api.utils.config import engine
from api.shared.helper import get_wita


# ============================================================================ #
#                   #SECTION - CREATE PURCHASE REQUEST                        #
# ============================================================================ #

# ======================= #ANCHOR - ACTIVE PEGAWAI ========================== #

def get_active_pegawai(conn, id_pegawai: int):

    sql = text("""
        SELECT
            id_pegawai, nama_lengkap, id_departemen
        FROM pegawai
        WHERE
            id_pegawai = :id_pegawai
            AND status = 1
        LIMIT 1
    """)

    return conn.execute(
        sql,
        {"id_pegawai": id_pegawai}
    ).mappings().first()


# ===================== #ANCHOR - ACTIVE DEPARTEMEN ========================== #

def get_active_departemen(conn, id_departemen: int):

    sql = text("""
        SELECT
            id_departemen, nama_departemen
        FROM ref_departemen
        WHERE
            id_departemen = :id_departemen
            AND status = 1
        LIMIT 1
    """)

    return conn.execute(
        sql,
        {"id_departemen": id_departemen}
    ).mappings().first()


# ===================== #ANCHOR - GENERATE REQUEST NUMBER ==================== #

def generate_request_number(conn):
    
    #? tambahkan WHERE is_active = 1 dibawah FROM apabila request_number ingin berurutan

    sql = text("""
        SELECT
            'AR-' ||
            TO_CHAR(CURRENT_DATE, 'YYYY-MM') ||
            '-' ||
            LPAD(
                (
                    SELECT COUNT(*) + 1
                    FROM purchase_requests
                    WHERE
                        EXTRACT(YEAR FROM tanggal_request) = EXTRACT(YEAR FROM CURRENT_DATE)
                        AND EXTRACT(MONTH FROM tanggal_request) = EXTRACT(MONTH FROM CURRENT_DATE)
                )::TEXT,
                4,
                '0'
            ) AS request_number
    """)

    return conn.execute(sql).scalar()


# ======================= #ANCHOR - CREATE REQUEST ========================== #

def create_purchase_request(conn, body: dict):

    sql = text("""
        INSERT INTO purchase_requests (
            request_number, id_pegawai, id_departemen, tanggal_request, nama_pekerjaan, priority, note, 
            total_amount, payment_description, payment_bank, payment_account_number, payment_account_name, 
            attachment_name, attachment_path, status, is_active, created_at, updated_at
        )
        VALUES (
            :request_number, :id_pegawai, :id_departemen, :tanggal_request, :nama_pekerjaan, :priority, :note, 
            :total_amount, :payment_description, :payment_bank, :payment_account_number, :payment_account_name, 
            :attachment_name, :attachment_path, :status, :is_active, :created_at, :updated_at
        )
        RETURNING id_request
    """)

    return conn.execute(
        sql,
        {
            "request_number": body["request_number"],
            "id_pegawai": body["id_pegawai"],
            "id_departemen": body["id_departemen"],
            "tanggal_request": body.get("tanggal_request"),
            "nama_pekerjaan": body["nama_pekerjaan"],
            "priority": body["priority"],
            "note": body.get("note"),
            "total_amount": body["total_amount"],
            "payment_description": body.get("payment_description"),
            "payment_bank": body.get("payment_bank"),
            "payment_account_number": body.get("payment_account_number"),
            "payment_account_name": body.get("payment_account_name"),
            "attachment_name": body.get("attachment_name"),
            "attachment_path": body.get("attachment_path"),
            "status": body["status"],
            "is_active": body["is_active"],
            "created_at": body["created_at"],
            "updated_at": body["updated_at"]
        }
    ).scalar()


# ======================== #ANCHOR - CREATE ITEMS =========================== #

def create_purchase_request_items(conn, id_request: int, items: list, now):

    sql = text("""
        INSERT INTO purchase_request_items (
            id_request, item_no, keterangan, unit, harga_satuan, jumlah, total, created_at, updated_at
        )
        VALUES (
            :id_request, :item_no, :keterangan, :unit, :harga_satuan, :jumlah, :total, :created_at, :updated_at
        )
    """)

    params = [
        {
            "id_request": id_request,
            "item_no": item["item_no"],
            "keterangan": item["keterangan"],
            "unit": item["unit"],
            "harga_satuan": item["harga_satuan"],
            "jumlah": item["jumlah"],
            "total": item["total"],
            "created_at": now,
            "updated_at": now
        }
        for item in items
    ]

    conn.execute(sql, params)


# ======================= #ANCHOR - CREATE HISTORY ========================== #

def create_purchase_request_history(conn, id_request: int, status: str, nama_pegawai: str, note: str = None, now = None):

    sql = text("""
        INSERT INTO purchase_request_histories (
            id_request, status, nama_pegawai, note, is_active, created_at
        )
        VALUES (
            :id_request, :status, :nama_pegawai, :note, 1, :created_at
        )
    """)

    conn.execute(
        sql,
        {
            "id_request": id_request,
            "status": status,
            "nama_pegawai": nama_pegawai,
            "note": note,
            "created_at": now or get_wita()
        }
    )

# ================ #!SECTION - CREATE PURCHASE REQUEST ====================== #



# ======================= #ANCHOR - LIST PURCHASE REQUEST ==================== #

def get_purchase_request_list(id_user: int, account_type: str, filters: dict):

    sql = """
        SELECT
            pr.id_request, pr.request_number, pr.id_pegawai, p.nama_lengkap AS nama_pegawai, pr.id_departemen, 
            d.nama_departemen, pr.tanggal_request, pr.nama_pekerjaan, pr.priority, pr.note, pr.total_amount, 
            pr.payment_description, pr.payment_bank, pr.payment_account_number, pr.payment_account_name, 
            pr.attachment_name, pr.attachment_path, pr.status, pr.created_at, pr.updated_at
        FROM purchase_requests pr
        JOIN pegawai p
            ON p.id_pegawai = pr.id_pegawai
        JOIN ref_departemen d
            ON d.id_departemen = pr.id_departemen
        WHERE
            pr.is_active = 1
    """

    params = {}

    # ============================================================
    # STATUS FILTER
    # ============================================================

    status = filters.get("status")

    if status == "ACTIVE":

        sql += """
            AND pr.status IN (
                'REQUESTED',
                'REVIEWED',
                'APPROVED'
            )
        """

    elif status:

        sql += """
            AND pr.status = :status
        """

        params["status"] = status

    # ============================================================
    # PEGAWAI
    # ============================================================

    if account_type == "pegawai":
        sql += """
            AND pr.id_pegawai = :id_pegawai
        """
        params["id_pegawai"] = id_user

    # ============================================================
    # DEPARTEMEN
    # ============================================================

    if filters.get("id_departemen"):
        sql += """
            AND pr.id_departemen = :id_departemen
        """

        params["id_departemen"] = int(
            filters["id_departemen"]
        )

    # ============================================================
    # TANGGAL MULAI
    # ============================================================

    if filters.get("tanggal_mulai"):
        sql += """
            AND pr.tanggal_request >= :tanggal_mulai
        """

        params["tanggal_mulai"] = (
            filters["tanggal_mulai"]
        )

    # ============================================================
    # TANGGAL SELESAI
    # ============================================================

    if filters.get("tanggal_selesai"):
        sql += """
            AND pr.tanggal_request <= :tanggal_selesai
        """

        params["tanggal_selesai"] = (
            filters["tanggal_selesai"]
        )

    # ============================================================
    # ORDER
    # ============================================================

    sql += """
        ORDER BY
            pr.tanggal_request DESC,
            pr.created_at DESC
    """

    with engine.connect() as conn:
        return conn.execute(
            text(sql),
            params
        ).mappings().all()


# ===================== #ANCHOR - DATA HISTORY ========================= #

def get_purchase_request_data_history(id_user: int, account_type: str, filters: dict):

    status = filters.get("status") or "PAID"
    page = filters.get("page", 1)
    limit = filters.get("limit", 10)
    offset = (page - 1) * limit

    sql = """
        SELECT
            pr.id_request, pr.request_number, pr.id_pegawai, p.nama_lengkap AS nama_pegawai, pr.id_departemen, 
            d.nama_departemen, pr.tanggal_request, pr.nama_pekerjaan, pr.priority, pr.total_amount, pr.status, 
            h.created_at AS status_changed_at
        FROM purchase_request_histories h
        INNER JOIN purchase_requests pr
            ON pr.id_request = h.id_request
        INNER JOIN pegawai p
            ON p.id_pegawai = pr.id_pegawai
        INNER JOIN ref_departemen d
            ON d.id_departemen = pr.id_departemen
        WHERE
            pr.is_active = 1
            AND h.is_active = 1
            AND h.status = :status
    """

    params = {
        "status": status,
        "limit": limit,
        "offset": offset
    }

    # ============================================================
    # USER / PEGAWAI
    # ============================================================

    if account_type == "pegawai":
        sql += """
            AND pr.id_pegawai = :id_pegawai
        """
        params["id_pegawai"] = id_user

    # ============================================================
    # FILTER TANGGAL HISTORY
    # ============================================================

    if filters.get("tanggal_mulai"):
        sql += """
            AND h.created_at >= CAST(:tanggal_mulai AS DATE)
        """
        params["tanggal_mulai"] = filters["tanggal_mulai"]

    if filters.get("tanggal_selesai"):
        sql += """
            AND h.created_at < (
                CAST(:tanggal_selesai AS DATE)
                + INTERVAL '1 day'
            )
        """
        params["tanggal_selesai"] = filters["tanggal_selesai"]

    # ============================================================
    # ORDER + PAGINATION
    # ============================================================

    sql += """
        ORDER BY
            h.created_at DESC
        LIMIT :limit
        OFFSET :offset
    """

    with engine.connect() as conn:
        rows = conn.execute(
            text(sql),
            params
        ).mappings().all()

        return [dict(row) for row in rows]


# ============================================================================ #
#                    #SECTION - DETAIL PURCHASE REQUEST                       #
# ============================================================================ #

# ======================= #ANCHOR - DETAIL REQUEST =========================== #

def get_purchase_request_detail(id_request: int, account_type: str, id_pegawai: int = None):
    
    request_sql = """
        SELECT
            pr.id_request, pr.request_number, pr.tanggal_request, pr.nama_pekerjaan, pr.priority, pr.status, pr.note, 
            pr.total_amount, p.id_pegawai, p.nama_lengkap, d.id_departemen, d.nama_departemen, pr.payment_description, 
            pr.payment_bank, pr.payment_account_number, pr.payment_account_name, pr.attachment_name, pr.attachment_path, 
            pr.created_at, pr.updated_at
        FROM purchase_requests pr
        INNER JOIN pegawai p
            ON p.id_pegawai = pr.id_pegawai
        INNER JOIN ref_departemen d
            ON d.id_departemen = pr.id_departemen
        WHERE
            pr.id_request = :id_request
            AND pr.is_active = 1
    """

    params = {
        "id_request": id_request
    }

    if account_type == "pegawai":
        request_sql += """
            AND pr.id_pegawai = :id_pegawai
        """

        params["id_pegawai"] = id_pegawai

    with engine.connect() as conn:

        request = conn.execute(
            text(request_sql),
            params
        ).mappings().first()

        if not request:
            return None

        items = conn.execute(
            text("""
                SELECT
                    id_item, item_no, keterangan, unit, harga_satuan, jumlah, total
                FROM purchase_request_items
                WHERE
                    id_request = :id_request
                ORDER BY
                    item_no ASC
            """),
            {
                "id_request": id_request
            }
        ).mappings().all()

        histories = conn.execute(
            text("""
                SELECT
                    id_history, status, nama_pegawai, note, created_at
                FROM purchase_request_histories
                WHERE
                    id_request = :id_request
                    AND is_active = 1
                ORDER BY
                    created_at ASC,
                    id_history ASC
            """),
            {
                "id_request": id_request
            }
        ).mappings().all()

    return {
        "id_request": request["id_request"],
        "request_number": request["request_number"],
        "tanggal_request": request["tanggal_request"],
        "nama_pekerjaan": request["nama_pekerjaan"],
        "priority": request["priority"],
        "status": request["status"],
        "note": request["note"],
        "total_amount": request["total_amount"],
        "pegawai": {
            "id_pegawai": request["id_pegawai"],
            "nama_lengkap": request["nama_lengkap"]
        },
        "departemen": {
            "id_departemen": request["id_departemen"],
            "nama_departemen": request["nama_departemen"]
        },
        "payment": {
            "description": request["payment_description"],
            "bank": request["payment_bank"],
            "account_number": request["payment_account_number"],
            "account_name": request["payment_account_name"]
        },
        "attachment": (
            {
                "name": request["attachment_name"],
                "path": request["attachment_path"]
            }
            if request["attachment_path"]
            else None
        ),
        "items": items,
        "history": histories,
        "created_at": request["created_at"],
        "updated_at": request["updated_at"]
    }



# ============================================================================ #
#                    #SECTION - UPDATE PURCHASE REQUEST                       #
# ============================================================================ #

# ======================= #ANCHOR - REQUEST FOR UPDATE ======================= #

def get_purchase_request_for_update(id_request: int, id_pegawai: int):

    sql = text("""
        SELECT
            pr.id_request,
            pr.request_number,
            pr.id_pegawai,
            pr.status,
            p.nama_lengkap AS nama_pegawai
        FROM purchase_requests pr
        INNER JOIN pegawai p
            ON p.id_pegawai = pr.id_pegawai
        WHERE
            pr.id_request = :id_request
            AND pr.id_pegawai = :id_pegawai
            AND pr.is_active = 1
        LIMIT 1
    """)

    with engine.connect() as conn:
        return conn.execute(
            sql,
            {
                "id_request": id_request,
                "id_pegawai": id_pegawai
            }
        ).mappings().first()


# ======================= #ANCHOR - ACTIVE DEPARTMENT ======================== #

def get_active_department(id_departemen: int):

    sql = text("""
        SELECT
            id_departemen, nama_departemen
        FROM ref_departemen
        WHERE
            id_departemen = :id_departemen
            AND status = 1
        LIMIT 1
    """)

    with engine.connect() as conn:
        return conn.execute(
            sql,
            {
                "id_departemen": id_departemen
            }
        ).mappings().first()


# ======================= #ANCHOR - UPDATE REQUEST =========================== #

def update_purchase_request(conn, id_request: int, body: dict, total_amount, now):

    fields = []
    params = {
        "id_request": id_request,
        "now": now
    }

    if "tanggal_request" in body:
        fields.append("tanggal_request = :tanggal_request")
        params["tanggal_request"] = body["tanggal_request"]

    if "id_departemen" in body:
        fields.append("id_departemen = :id_departemen")
        params["id_departemen"] = body["id_departemen"]

    if "nama_pekerjaan" in body:
        fields.append("nama_pekerjaan = :nama_pekerjaan")
        params["nama_pekerjaan"] = body["nama_pekerjaan"]

    if "priority" in body:
        fields.append("priority = :priority")
        params["priority"] = body["priority"]

    if "note" in body:
        fields.append("note = :note")
        params["note"] = body["note"]

    if "payment_description" in body:
        fields.append("payment_description = :payment_description")
        params["payment_description"] = body["payment_description"]

    if "payment_bank" in body:
        fields.append("payment_bank = :payment_bank")
        params["payment_bank"] = body["payment_bank"]

    if "payment_account_number" in body:
        fields.append("payment_account_number = :payment_account_number")
        params["payment_account_number"] = body["payment_account_number"]

    if "payment_account_name" in body:
        fields.append("payment_account_name = :payment_account_name")
        params["payment_account_name"] = body["payment_account_name"]

    if "attachment_name" in body:
        fields.append("attachment_name = :attachment_name")
        params["attachment_name"] = body["attachment_name"]

    if "attachment_path" in body:
        fields.append("attachment_path = :attachment_path")
        params["attachment_path"] = body["attachment_path"]

    if total_amount is not None:
        fields.append("total_amount = :total_amount")
        params["total_amount"] = total_amount

    if not fields:
        return

    fields.append("updated_at = :now")

    sql = text(f"""
        UPDATE purchase_requests
        SET
            {", ".join(fields)}
        WHERE
            id_request = :id_request
            AND is_active = 1
    """)

    conn.execute(sql, params)


# ======================== #ANCHOR - DELETE ITEMS ============================ #

def delete_purchase_request_items(conn, id_request: int):

    sql = text("""
        DELETE FROM purchase_request_items
        WHERE
            id_request = :id_request
    """)

    conn.execute(
        sql,
        {
            "id_request": id_request
        }
    )


# ======================== #ANCHOR - CREATE ITEMS ============================ #

def create_purchase_request_items(conn, id_request: int, items: list, now):

    sql = text("""
        INSERT INTO purchase_request_items (
            id_request, item_no, keterangan, unit, harga_satuan, jumlah, total, created_at, updated_at
        )
        VALUES (
            :id_request, :item_no, :keterangan, :unit, :harga_satuan, :jumlah, :total, :now, :now
        )
    """)

    params = [
        {
            "id_request": id_request,
            "item_no": item["item_no"],
            "keterangan": item["keterangan"],
            "unit": item["unit"],
            "harga_satuan": item["harga_satuan"],
            "jumlah": item["jumlah"],
            "total": item["total"],
            "now": now
        }
        for item in items
    ]

    conn.execute(sql, params)


# ======================= #ANCHOR - UPDATE STATUS ============================ #

def update_purchase_request_status(conn, id_request: int, status: str, now):

    sql = text("""
        UPDATE purchase_requests
        SET
            status = :status,
            updated_at = :now
        WHERE
            id_request = :id_request
            AND is_active = 1
    """)

    conn.execute(
        sql,
        {
            "id_request": id_request,
            "status": status,
            "now": now
        }
    )


# ======================= #ANCHOR - CREATE HISTORY ============================ #

def create_purchase_request_history(conn, id_request: int, status: str, nama_pegawai: str, note, now):

    sql = text("""
        INSERT INTO purchase_request_histories (
            id_request, status, nama_pegawai, note, is_active, created_at
        )
        VALUES (
            :id_request, :status, :nama_pegawai, :note, 1, :now
        )
    """)

    conn.execute(
        sql,
        {
            "id_request": id_request,
            "status": status,
            "nama_pegawai": nama_pegawai,
            "note": note,
            "now": now
        }
    )

# ================== #!SECTION - UPDATE PURCHASE REQUEST ===================== #

# ======================= #ANCHOR - REQUEST FOR DELETE ======================== #

def get_purchase_request_for_delete(conn, id_request: int, id_pegawai: int = None):

    sql = """
        SELECT
            id_request, id_pegawai, status
        FROM purchase_requests
        WHERE
            id_request = :id_request
            AND is_active = 1
    """

    params = {
        "id_request": id_request
    }

    if id_pegawai is not None:
        sql += """
            AND id_pegawai = :id_pegawai
        """

        params["id_pegawai"] = id_pegawai

    sql += """
        LIMIT 1
    """

    return conn.execute(
        text(sql),
        params
    ).mappings().first()


# ======================= #ANCHOR - SOFT DELETE REQUEST ===================== #

def update_purchase_request_inactive(conn, id_request: int):

    sql = text("""
        UPDATE purchase_requests
        SET
            is_active = 0,
            updated_at = :now
        WHERE
            id_request = :id_request
            AND is_active = 1
    """)

    conn.execute(
        sql,
        {
            "id_request": id_request,
            "now": get_wita()
        }
    )

# ================== #!SECTION - DELETE PURCHASE REQUEST ===================== #

# ==================== #!SECTION - DETAIL PURCHASE REQUEST =================== #



# ============================================================================ #
#                            #SECTION - STATUS UPDATE                          #
# ============================================================================ #

# ======================= #ANCHOR - REQUEST FOR REVIEW ======================== #

def get_purchase_request_for_status_update(conn, id_request: int):

    sql = text("""
        SELECT
            id_request, request_number, status, is_active
        FROM purchase_requests
        WHERE
            id_request = :id_request
            AND is_active = 1
        LIMIT 1
    """)

    return conn.execute(
        sql,
        {
            "id_request": id_request
        }
    ).mappings().first()


# ========================= #!SECTION - STATUS UPDATE ======================== #



# ============================================================================ #
#                    #SECTION - PURCHASE REQUEST HISTORY                       #
# ============================================================================ #

# ======================= #ANCHOR - REQUEST OWNER ============================ #

def get_purchase_request_owner(id_request: int):

    sql = text("""
        SELECT
            id_request,
            id_pegawai
        FROM purchase_requests
        WHERE
            id_request = :id_request
            AND is_active = 1
        LIMIT 1
    """)

    with engine.connect() as conn:
        return conn.execute(
            sql,
            {
                "id_request": id_request
            }
        ).mappings().first()


# ======================= #ANCHOR - REQUEST HISTORY ========================== #

def get_purchase_request_history(id_request: int):

    sql = text("""
        SELECT
            id_history, id_request, status, nama_pegawai, note, created_at
        FROM purchase_request_histories
        WHERE
            id_request = :id_request
            AND is_active = 1
        ORDER BY
            created_at ASC,
            id_history ASC
    """)

    with engine.connect() as conn:
        return conn.execute(
            sql,
            {
                "id_request": id_request
            }
        ).mappings().all()

# ================== #!SECTION - PURCHASE REQUEST HISTORY ==================== #



# ============================================================================ #
#                     #SECTION - USER DASHBOARD                                #
# ============================================================================ #

# ======================= #ANCHOR - MY SUMMARY =============================== #

def get_purchase_request_dashboard_summary(id_pegawai: int):

    sql = text("""
        SELECT
            COUNT(*) AS total,
            COUNT(*) FILTER (WHERE status <> 'PAID') AS active,
            COUNT(*) FILTER (WHERE status = 'REQUESTED') AS requested,
            COUNT(*) FILTER (WHERE status = 'REVIEWED') AS reviewed,
            COUNT(*) FILTER (WHERE status = 'APPROVED') AS approved,
            COUNT(*) FILTER (WHERE status = 'REJECTED') AS rejected,
            (
                SELECT COUNT(DISTINCT h.id_request)
                FROM purchase_request_histories h
                INNER JOIN purchase_requests pr_paid
                    ON pr_paid.id_request = h.id_request
                WHERE
                    pr_paid.id_pegawai = :id_pegawai
                    AND pr_paid.is_active = 1
                    AND h.status = 'PAID'
                    AND h.is_active = 1
                    AND h.created_at >= DATE_TRUNC('month', CURRENT_DATE)
                    AND h.created_at < DATE_TRUNC(
                        'month',
                        CURRENT_DATE
                    ) + INTERVAL '1 month'
            ) AS paid
        FROM purchase_requests
        WHERE
            id_pegawai = :id_pegawai
            AND is_active = 1
    """)

    with engine.connect() as conn:
        row = conn.execute(
            sql,
            {
                "id_pegawai": id_pegawai
            }
        ).mappings().first()

        return dict(row)


def get_purchase_request_dashboard_list(id_pegawai: int):

    sql = text("""
        SELECT
            pr.id_request,
            pr.request_number,
            pr.nama_pekerjaan,
            pr.tanggal_request,
            pr.total_amount,
            pr.status,
            pr.priority,

            COALESCE(
                json_agg(
                    json_build_object(
                        'status', h.status,
                        'nama_pegawai', h.nama_pegawai,
                        'tanggal', h.created_at
                    )
                    ORDER BY h.created_at ASC
                ) FILTER (WHERE h.id_history IS NOT NULL),
                '[]'
            ) AS history

        FROM purchase_requests pr

        LEFT JOIN purchase_request_histories h
            ON h.id_request = pr.id_request
            AND h.is_active = 1

        WHERE
            pr.id_pegawai = :id_pegawai
            AND pr.is_active = 1
            AND pr.status != 'PAID'

        GROUP BY
            pr.id_request

        ORDER BY
            pr.created_at DESC
    """)

    with engine.connect() as conn:
        rows = conn.execute(
            sql,
            {"id_pegawai": id_pegawai}
        ).mappings().all()

        return [dict(row) for row in rows]

# ==================== #!SECTION - USER DASHBOARD ============================= #



# ============================================================================ #
#                       #SECTION - EXPORT PURCHASE REQUEST                     #
# ============================================================================ #

# ===================== #ANCHOR - DOWNLOAD PURCHASE REQUEST =================== #

def get_purchase_request_pdf(id_request: int, id_pegawai: int = None):

    sql = text("""
        SELECT
            pr.id_request,
            pr.request_number,
            pr.id_pegawai,
            p.nama_lengkap AS nama_pegawai,
            pr.id_departemen,
            d.nama_departemen,
            pr.tanggal_request,
            pr.nama_pekerjaan,
            pr.priority,
            pr.note,
            pr.total_amount,
            pr.payment_description,
            pr.payment_bank,
            pr.payment_account_number,
            pr.payment_account_name,
            pr.attachment_name,
            pr.attachment_path,
            pr.status,
            pr.created_at,
            pr.updated_at
        FROM purchase_requests pr

        INNER JOIN pegawai p
            ON p.id_pegawai = pr.id_pegawai

        INNER JOIN ref_departemen d
            ON d.id_departemen = pr.id_departemen

        WHERE
            pr.id_request = :id_request
            AND pr.is_active = 1

            AND (
                :id_pegawai IS NULL
                OR pr.id_pegawai = :id_pegawai
            )

        LIMIT 1
    """)

    with engine.connect() as conn:
        return conn.execute(
            sql,
            {
                "id_request": id_request,
                "id_pegawai": id_pegawai
            }
        ).mappings().first()


def get_purchase_request_pdf_items(id_request: int):

    sql = text("""
        SELECT
            id_item,
            item_no,
            keterangan,
            unit,
            harga_satuan,
            jumlah,
            total
        FROM purchase_request_items
        WHERE
            id_request = :id_request
        ORDER BY
            item_no ASC
    """)

    with engine.connect() as conn:
        return conn.execute(
            sql,
            {
                "id_request": id_request
            }
        ).mappings().all()


def get_purchase_request_pdf_history(id_request: int):

    sql = text("""
        SELECT
            id_history,
            status,
            nama_pegawai,
            note,
            created_at
        FROM purchase_request_histories
        WHERE
            id_request = :id_request
            AND is_active = 1
        ORDER BY
            created_at ASC
    """)

    with engine.connect() as conn:
        return conn.execute(
            sql,
            {
                "id_request": id_request
            }
        ).mappings().all()


# ==================== #!SECTION - EXPORT PURCHASE REQUEST =================== #
