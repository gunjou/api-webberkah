from sqlalchemy import text

from api.shared.exceptions import NotFoundError
from api.utils.config import engine
from api.shared.helper import get_wita


# ========================= #ANCHOR - HELPER FUNCTION ========================= #

def get_work_item_by_id(id_work_item):

    query = text("""
        SELECT
            id_work_item, work_number, work_name, work_type, current_stage, is_active
        FROM work_items
        WHERE id_work_item = :id_work_item
          AND is_active = 1
    """)

    with engine.connect() as conn:

        result = conn.execute(
            query,
            {
                "id_work_item": id_work_item
            }
        ).mappings().first()

    return dict(result) if result else None


def get_completion_by_id(id_completion):

    query = text("""
        SELECT
            id_completion, id_work_item, ba_number, ba_date, completion_date, is_active
        FROM work_completions
        WHERE id_completion = :id_completion
          AND is_active = 1
    """)

    with engine.connect() as conn:

        result = conn.execute(
            query,
            {
                "id_completion": id_completion
            }
        ).mappings().first()

    return dict(result) if result else None


def get_invoice_by_number(invoice_number, exclude_id=None):

    query = text("""
        SELECT
            id_invoice, invoice_number, id_work_item
        FROM work_invoices
        WHERE invoice_number = :invoice_number
          AND is_active = 1
          AND (
              :exclude_id IS NULL
              OR id_invoice != :exclude_id
          )
        LIMIT 1
    """)

    with engine.connect() as conn:

        result = conn.execute(
            query,
            {
                "invoice_number": invoice_number,
                "exclude_id": exclude_id
            }
        ).mappings().first()

    return dict(result) if result else None


def get_invoice_by_id(id_invoice):

    query = text("""
        SELECT
            id_invoice, id_work_item, id_completion, invoice_number, invoice_date, invoice_value, vat_rate, due_date, 
            document_url, notes, is_active
        FROM work_invoices
        WHERE id_invoice = :id_invoice
          AND is_active = 1
    """)

    with engine.connect() as conn:

        result = conn.execute(
            query,
            {
                "id_invoice": id_invoice
            }
        ).mappings().first()

    return dict(result) if result else None

# ============================================================================ #
#                               #SECTION - INVOICE                             #
# ============================================================================ #

def get_invoice_list(
    stage="ACTIVE",
    health_status=None,
    id_client=None,
    payment_status=None,
    search=None,
    page=None,
    per_page=None
):

    conditions = [
        "wi2.is_active = 1",
        "wi.is_active = 1"
    ]

    params = {}

    # ==========================================================
    # FILTER STAGE
    # ========================================================== #

    if stage == "CLOSED":

        conditions.append(
            "wi.current_stage = 'CLOSED'"
        )

    else:

        conditions.append(
            "wi.current_stage <> 'CLOSED'"
        )

    # ==========================================================
    # FILTER CLIENT
    # ========================================================== #

    if id_client:

        conditions.append(
            "wi.id_client = :id_client"
        )

        params["id_client"] = id_client

    # ==========================================================
    # FILTER SEARCH
    # ========================================================== #

    if search:

        conditions.append("""
            (
                wi2.invoice_number ILIKE :search
                OR wi.work_number ILIKE :search
                OR wi.work_name ILIKE :search
                OR c.name ILIKE :search
            )
        """)

        params["search"] = f"%{search.strip()}%"

    # ==========================================================
    # FILTER HEALTH
    # ========================================================== #

    if health_status:

        if health_status == "PAID":

            conditions.append("""
                COALESCE(
                    payment_summary.paid_amount,
                    0
                ) >= (
                    wi2.invoice_value
                    + (
                        wi2.invoice_value
                        * COALESCE(wi2.vat_rate, 0)
                        / 100
                    )
                )
            """)

        elif health_status == "OVERDUE":

            conditions.append("""
                COALESCE(
                    payment_summary.paid_amount,
                    0
                ) < (
                    wi2.invoice_value
                    + (
                        wi2.invoice_value
                        * COALESCE(wi2.vat_rate, 0)
                        / 100
                    )
                )
                AND wi2.due_date < CURRENT_DATE
            """)

        elif health_status == "DUE_SOON":

            conditions.append("""
                COALESCE(
                    payment_summary.paid_amount,
                    0
                ) < (
                    wi2.invoice_value
                    + (
                        wi2.invoice_value
                        * COALESCE(wi2.vat_rate, 0)
                        / 100
                    )
                )
                AND wi2.due_date >= CURRENT_DATE
                AND (
                    wi2.due_date - CURRENT_DATE
                ) <= 30
            """)

        elif health_status == "ON_TRACK":

            conditions.append("""
                COALESCE(
                    payment_summary.paid_amount,
                    0
                ) < (
                    wi2.invoice_value
                    + (
                        wi2.invoice_value
                        * COALESCE(wi2.vat_rate, 0)
                        / 100
                    )
                )
                AND wi2.due_date > CURRENT_DATE + 30
            """)

    # ==========================================================
    # FILTER PAYMENT
    # ========================================================== #

    if payment_status:

        if payment_status == "PAID":

            conditions.append("""
                COALESCE(
                    payment_summary.paid_amount,
                    0
                ) >= (
                    wi2.invoice_value
                    + (
                        wi2.invoice_value
                        * COALESCE(wi2.vat_rate, 0)
                        / 100
                    )
                )
            """)

        elif payment_status == "UNPAID":

            conditions.append("""
                COALESCE(
                    payment_summary.paid_amount,
                    0
                ) < (
                    wi2.invoice_value
                    + (
                        wi2.invoice_value
                        * COALESCE(wi2.vat_rate, 0)
                        / 100
                    )
                )
            """)

    where_clause = " AND ".join(conditions)

    # ==========================================================
    # PAGINATION
    # ========================================================== #

    pagination_clause = ""

    if stage == "CLOSED" and page is not None and per_page is not None:

        offset = (page - 1) * per_page

        params["limit"] = per_page
        params["offset"] = offset

        pagination_clause = """
            LIMIT :limit
            OFFSET :offset
        """

    # ==========================================================
    # DATA QUERY
    # ========================================================== #

    query = text(f"""
        SELECT
            wi2.id_invoice,
            wi2.id_work_item,

            wi.work_number,
            wi.work_name,
            wi.work_type,
            wi.current_stage,

            wi.id_client,

            c.code AS client_code,
            c.name AS client_name,

            (
                SELECT cp.name
                FROM client_pic cp
                WHERE cp.id_client_pic = wi.id_client_pic
                  AND cp.is_active = 1
                LIMIT 1
            ) AS client_pic_name,

            (
                SELECT wc2.id_contract
                FROM work_contracts wc2
                WHERE wc2.id_work_item = wi.id_work_item
                  AND wc2.is_active = 1
                ORDER BY
                    wc2.contract_date DESC NULLS LAST,
                    wc2.id_contract DESC
                LIMIT 1
            ) AS id_contract,

            (
                SELECT wc2.contract_number
                FROM work_contracts wc2
                WHERE wc2.id_work_item = wi.id_work_item
                  AND wc2.is_active = 1
                ORDER BY
                    wc2.contract_date DESC NULLS LAST,
                    wc2.id_contract DESC
                LIMIT 1
            ) AS contract_number,

            wi2.id_completion,
            wc.ba_number,

            wi2.invoice_number,
            wi2.invoice_date,

            -- ================= INVOICE ================= #

            wi2.invoice_value,
            wi2.vat_rate,

            ROUND(
                wi2.invoice_value
                * COALESCE(wi2.vat_rate, 0)
                / 100,
                2
            ) AS vat_amount,

            ROUND(
                wi2.invoice_value
                + (
                    wi2.invoice_value
                    * COALESCE(wi2.vat_rate, 0)
                    / 100
                ),
                2
            ) AS total_invoice,

            wi2.due_date,
            wi2.document_url,
            wi2.notes,

            -- ================= PAYMENT ================= #

            payment_summary.id_payment,

            COALESCE(
                payment_summary.paid_amount,
                0
            ) AS paid_amount,

            GREATEST(
                (
                    wi2.invoice_value
                    + (
                        wi2.invoice_value
                        * COALESCE(wi2.vat_rate, 0)
                        / 100
                    )
                )
                - COALESCE(
                    payment_summary.paid_amount,
                    0
                ),
                0
            ) AS outstanding_amount,

            CASE
                WHEN COALESCE(
                    payment_summary.paid_amount,
                    0
                ) = 0
                    THEN 'BELUM_DIBAYAR'

                WHEN COALESCE(
                    payment_summary.paid_amount,
                    0
                ) < (
                    wi2.invoice_value
                    + (
                        wi2.invoice_value
                        * COALESCE(wi2.vat_rate, 0)
                        / 100
                    )
                )
                    THEN 'SEBAGIAN_DIBAYAR'

                ELSE 'SUDAH_DIBAYAR'
            END AS payment_status,

            -- ================= HEALTH ================= #

            CASE
                WHEN COALESCE(
                    payment_summary.paid_amount,
                    0
                ) >= (
                    wi2.invoice_value
                    + (
                        wi2.invoice_value
                        * COALESCE(wi2.vat_rate, 0)
                        / 100
                    )
                )
                    THEN 'PAID'

                WHEN wi2.due_date < CURRENT_DATE
                    THEN 'OVERDUE'

                WHEN (
                    wi2.due_date - CURRENT_DATE
                ) <= 30
                    THEN 'DUE_SOON'

                ELSE 'ON_TRACK'
            END AS health_status,

            CASE
                WHEN COALESCE(
                    payment_summary.paid_amount,
                    0
                ) >= (
                    wi2.invoice_value
                    + (
                        wi2.invoice_value
                        * COALESCE(wi2.vat_rate, 0)
                        / 100
                    )
                )
                    THEN NULL

                ELSE (
                    wi2.due_date - CURRENT_DATE
                )
            END AS days_to_due,

            -- ================= AUDIT ================= #

            wi2.is_active,
            wi2.created_by,
            wi2.created_at,
            wi2.updated_by,
            wi2.updated_at

        FROM work_invoices wi2

        INNER JOIN work_items wi
            ON wi.id_work_item = wi2.id_work_item

        LEFT JOIN client c
            ON c.id_client = wi.id_client
           AND c.is_active = 1

        LEFT JOIN work_completions wc
            ON wc.id_completion = wi2.id_completion
           AND wc.is_active = 1

        LEFT JOIN (
            SELECT
                id_invoice,
                SUM(amount) AS paid_amount,
                MAX(id_payment) AS id_payment
            FROM work_payments
            WHERE is_active = 1
            GROUP BY id_invoice
        ) payment_summary
            ON payment_summary.id_invoice = wi2.id_invoice

        WHERE {where_clause}

        ORDER BY
            wi2.invoice_date DESC NULLS LAST,
            wi2.id_invoice DESC

        {pagination_clause}
    """)

    # ==========================================================
    # COUNT QUERY
    # ========================================================== #

    count_query = text(f"""
        SELECT COUNT(*)

        FROM work_invoices wi2

        INNER JOIN work_items wi
            ON wi.id_work_item = wi2.id_work_item

        LEFT JOIN client c
            ON c.id_client = wi.id_client
           AND c.is_active = 1

        LEFT JOIN (
            SELECT
                id_invoice,
                SUM(amount) AS paid_amount
            FROM work_payments
            WHERE is_active = 1
            GROUP BY id_invoice
        ) payment_summary
            ON payment_summary.id_invoice = wi2.id_invoice

        WHERE {where_clause}
    """)

    # ==========================================================
    # EXECUTE
    # ========================================================== #

    with engine.connect() as conn:

        result = conn.execute(
            query,
            params
        ).mappings().all()

        total = conn.execute(
            count_query,
            params
        ).scalar()

    # ==========================================================
    # RESPONSE
    # ========================================================== #

    response = {
        "items": [dict(row) for row in result],
        "total": total
    }

    if stage == "CLOSED" and page is not None and per_page is not None:

        response["pagination"] = {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": (
                (total + per_page - 1) // per_page
            )
        }

    return response


def create_invoice(id_work_item, id_completion, invoice_number, invoice_date, invoice_value, vat_rate, due_date, document_url, notes, created_by):

    now = get_wita()

    with engine.begin() as conn:

        # ============================= 1. INSERT INVOICE ============================ #

        insert_invoice_query = text("""
            INSERT INTO work_invoices (
                id_work_item, id_completion, invoice_number, invoice_date, invoice_value, vat_rate, due_date, 
                document_url, notes, is_active, created_by, created_at, updated_at
            )
            VALUES (
                :id_work_item, :id_completion, :invoice_number, :invoice_date, :invoice_value, :vat_rate, :due_date, 
                :document_url, :notes, 1, :created_by, :created_at, :updated_at
            )
            RETURNING
                id_invoice, id_work_item, id_completion, invoice_number, invoice_date, invoice_value, vat_rate, due_date, 
                document_url, notes, is_active, created_by, created_at
        """)

        result = conn.execute(
            insert_invoice_query,
            {
                "id_work_item": id_work_item,
                "id_completion": id_completion,
                "invoice_number": invoice_number,
                "invoice_date": invoice_date,
                "invoice_value": invoice_value,
                "vat_rate": vat_rate,
                "due_date": due_date,
                "document_url": document_url,
                "notes": notes,
                "created_by": created_by,
                "created_at": now,
                "updated_at": now
            }
        ).mappings().first()

        invoice = dict(result)

        # ========================= 2. CLOSE BA STAGE HISTORY ======================== #

        close_history_query = text("""
            UPDATE work_stage_histories
            SET
                ended_at = :ended_at
            WHERE
                id_work_item = :id_work_item
                AND stage = 'BA'
                AND ended_at IS NULL
                AND is_active = 1
        """)

        conn.execute(
            close_history_query,
            {
                "id_work_item": id_work_item,
                "ended_at": now
            }
        )

        # ========================= 3. UPDATE WORK ITEM STAGE ======================== #

        update_work_query = text("""
            UPDATE work_items
            SET
                current_stage = 'INVOICE',
                updated_by = :updated_by,
                updated_at = :updated_at
            WHERE
                id_work_item = :id_work_item
                AND is_active = 1
        """)

        conn.execute(
            update_work_query,
            {
                "id_work_item": id_work_item,
                "updated_by": created_by,
                "updated_at": now
            }
        )

        # ====================== 4. CREATE INVOICE STAGE HISTORY ===================== #
        
        insert_history_query = text("""
            INSERT INTO work_stage_histories (
                id_work_item, stage, started_at, ended_at, notes, is_active, created_by, created_at
            )
            VALUES (
                :id_work_item, 'INVOICE', :started_at, NULL, :notes, 1, :created_by, :created_at
            )
        """)

        conn.execute(
            insert_history_query,
            {
                "id_work_item": id_work_item,
                "started_at": now,
                "notes": "Stage berubah menjadi INVOICE setelah invoice dibuat.",
                "created_by": created_by,
                "created_at": now
            }
        )

    return invoice


def get_invoice_detail(id_invoice):

    # ================================ INVOICE DETAIL ================================ #

    query = text("""
        SELECT
            wi2.id_invoice,
            wi2.id_work_item,

            -- ============================== WORK ITEM ============================== #

            wi.work_number,
            wi.work_name,
            wi.work_type,
            wi.current_stage,
            wi.progress_percent,
            wi.start_date,
            wi.target_end_date,
            wi.completion_date,
            wi.notes AS work_notes,

            -- ================================= CLIENT =============================== #

            wi.id_client,
            c.code AS client_code,
            c.name AS client_name,
            c.address AS client_address,
            c.phone AS client_phone,
            c.email AS client_email,

            -- ================================= CLIENT PIC =========================== #

            wi.id_client_pic,
            cp.name AS client_pic_name,
            cp.position AS client_pic_position,
            cp.phone AS client_pic_phone,
            cp.email AS client_pic_email,

            -- ================================ INTERNAL PIC ========================= #

            wi.internal_pic_name,

            -- ================================= CONTRACT ============================= #

            (
                SELECT wc2.id_contract
                FROM work_contracts wc2
                WHERE wc2.id_work_item = wi.id_work_item
                  AND wc2.is_active = 1
                ORDER BY
                    wc2.contract_date DESC NULLS LAST,
                    wc2.id_contract DESC
                LIMIT 1
            ) AS id_contract,

            (
                SELECT wc2.contract_number
                FROM work_contracts wc2
                WHERE wc2.id_work_item = wi.id_work_item
                  AND wc2.is_active = 1
                ORDER BY
                    wc2.contract_date DESC NULLS LAST,
                    wc2.id_contract DESC
                LIMIT 1
            ) AS contract_number,

            (
                SELECT wc2.contract_date
                FROM work_contracts wc2
                WHERE wc2.id_work_item = wi.id_work_item
                  AND wc2.is_active = 1
                ORDER BY
                    wc2.contract_date DESC NULLS LAST,
                    wc2.id_contract DESC
                LIMIT 1
            ) AS contract_date,

            (
                SELECT wc2.start_date
                FROM work_contracts wc2
                WHERE wc2.id_work_item = wi.id_work_item
                  AND wc2.is_active = 1
                ORDER BY
                    wc2.contract_date DESC NULLS LAST,
                    wc2.id_contract DESC
                LIMIT 1
            ) AS contract_start_date,

            (
                SELECT wc2.end_date
                FROM work_contracts wc2
                WHERE wc2.id_work_item = wi.id_work_item
                  AND wc2.is_active = 1
                ORDER BY
                    wc2.contract_date DESC NULLS LAST,
                    wc2.id_contract DESC
                LIMIT 1
            ) AS contract_end_date,

            (
                SELECT wc2.contract_value
                FROM work_contracts wc2
                WHERE wc2.id_work_item = wi.id_work_item
                  AND wc2.is_active = 1
                ORDER BY
                    wc2.contract_date DESC NULLS LAST,
                    wc2.id_contract DESC
                LIMIT 1
            ) AS contract_value,

            (
                SELECT wc2.vat_rate
                FROM work_contracts wc2
                WHERE wc2.id_work_item = wi.id_work_item
                  AND wc2.is_active = 1
                ORDER BY
                    wc2.contract_date DESC NULLS LAST,
                    wc2.id_contract DESC
                LIMIT 1
            ) AS contract_vat_rate,

            -- ==================================== BA ================================ #

            wi2.id_completion,
            wc.ba_number,
            wc.ba_date,
            wc.completion_date,
            wc.document_url AS ba_document_url,
            wc.notes AS ba_notes,

            -- ================================= INVOICE ============================== #

            wi2.invoice_number,
            wi2.invoice_date,
            wi2.invoice_value,
            wi2.vat_rate,

            ROUND(
                wi2.invoice_value
                * COALESCE(wi2.vat_rate, 0)
                / 100,
                2
            ) AS vat_amount,

            ROUND(
                wi2.invoice_value
                + (
                    wi2.invoice_value
                    * COALESCE(wi2.vat_rate, 0)
                    / 100
                ),
                2
            ) AS total_invoice,

            wi2.due_date,
            wi2.document_url AS invoice_document_url,
            wi2.notes AS invoice_notes,

            -- ================================= PAYMENT ============================== #

            COALESCE(
                payment_summary.paid_amount,
                0
            ) AS paid_amount,

            GREATEST(
                (
                    wi2.invoice_value
                    + (
                        wi2.invoice_value
                        * COALESCE(wi2.vat_rate, 0)
                        / 100
                    )
                )
                - COALESCE(payment_summary.paid_amount, 0),
                0
            ) AS outstanding_amount,

            CASE
                WHEN COALESCE(payment_summary.paid_amount, 0) = 0
                    THEN 'BELUM_DIBAYAR'

                WHEN COALESCE(payment_summary.paid_amount, 0)
                     < (
                        wi2.invoice_value
                        + (
                            wi2.invoice_value
                            * COALESCE(wi2.vat_rate, 0)
                            / 100
                        )
                     )
                    THEN 'SEBAGIAN_DIBAYAR'

                ELSE 'SUDAH_DIBAYAR'
            END AS payment_status,

            -- ================================= HEALTH =============================== #

            CASE
                WHEN COALESCE(payment_summary.paid_amount, 0)
                     >= (
                        wi2.invoice_value
                        + (
                            wi2.invoice_value
                            * COALESCE(wi2.vat_rate, 0)
                            / 100
                        )
                     )
                    THEN 'PAID'

                WHEN wi2.due_date < CURRENT_DATE
                    THEN 'OVERDUE'

                WHEN (
                    wi2.due_date - CURRENT_DATE
                ) <= 30
                    THEN 'DUE_SOON'

                ELSE 'ON_TRACK'
            END AS health_status,

            CASE
                WHEN COALESCE(payment_summary.paid_amount, 0)
                     >= (
                        wi2.invoice_value
                        + (
                            wi2.invoice_value
                            * COALESCE(wi2.vat_rate, 0)
                            / 100
                        )
                     )
                    THEN NULL

                ELSE (
                    wi2.due_date - CURRENT_DATE
                )
            END AS days_to_due,

            -- ================================= AUDIT ================================= #

            wi2.is_active,
            wi2.created_by,
            wi2.created_at,
            wi2.updated_by,
            wi2.updated_at

        FROM work_invoices wi2

        INNER JOIN work_items wi
            ON wi.id_work_item = wi2.id_work_item

        LEFT JOIN client c
            ON c.id_client = wi.id_client
           AND c.is_active = 1

        LEFT JOIN client_pic cp
            ON cp.id_client_pic = wi.id_client_pic
           AND cp.is_active = 1

        LEFT JOIN work_completions wc
            ON wc.id_completion = wi2.id_completion
           AND wc.is_active = 1

        LEFT JOIN (
            SELECT
                id_invoice,
                SUM(amount) AS paid_amount
            FROM work_payments
            WHERE is_active = 1
            GROUP BY id_invoice
        ) payment_summary
            ON payment_summary.id_invoice = wi2.id_invoice

        WHERE wi2.id_invoice = :id_invoice
          AND wi2.is_active = 1
          AND wi.is_active = 1
    """)

    # ================================ PAYMENT HISTORY ================================ #

    payment_query = text("""
        SELECT
            id_payment, id_invoice, payment_date, amount, document_url, notes, is_active, created_by, created_at, updated_by, updated_at
        FROM work_payments
        WHERE id_invoice = :id_invoice
          AND is_active = 1
        ORDER BY
            payment_date DESC,
            id_payment DESC
    """)

    # ================================== EXECUTE ================================== #

    with engine.connect() as conn:

        result = conn.execute(
            query,
            {
                "id_invoice": id_invoice
            }
        ).mappings().first()

        if not result:
            return None

        payments = conn.execute(
            payment_query,
            {
                "id_invoice": id_invoice
            }
        ).mappings().all()

    data = dict(result)

    data["payments"] = [
        dict(payment)
        for payment in payments
    ]

    return data


def update_invoice(id_invoice, id_work_item, id_completion, invoice_number, invoice_date, invoice_value, vat_rate, due_date, document_url, notes, updated_by):

    query = text("""
        UPDATE work_invoices
        SET
            id_work_item = :id_work_item,
            id_completion = :id_completion,
            invoice_number = :invoice_number,
            invoice_date = :invoice_date,
            invoice_value = :invoice_value,
            vat_rate = :vat_rate,
            due_date = :due_date,
            document_url = :document_url,
            notes = :notes,
            updated_by = :updated_by,
            updated_at = :updated_at
        WHERE id_invoice = :id_invoice
          AND is_active = 1
    """)

    with engine.begin() as conn:

        conn.execute(
            query,
            {
                "id_invoice": id_invoice,
                "id_work_item": id_work_item,
                "id_completion": id_completion,
                "invoice_number": invoice_number,
                "invoice_date": invoice_date,
                "invoice_value": invoice_value,
                "vat_rate": vat_rate,
                "due_date": due_date,
                "document_url": document_url,
                "notes": notes,
                "updated_by": updated_by,
                "updated_at": get_wita()
            }
        )


def delete_invoice(id_invoice, id_work_item, updated_by):

    now = get_wita()

    with engine.begin() as conn:

        # ====================== 1. SOFT DELETE INVOICE ====================== #

        delete_invoice_query = text("""
            UPDATE work_invoices
            SET
                is_active = 0,
                updated_by = :updated_by,
                updated_at = :updated_at
            WHERE
                id_invoice = :id_invoice
                AND is_active = 1
        """)

        result = conn.execute(
            delete_invoice_query,
            {
                "id_invoice": id_invoice,
                "updated_by": updated_by,
                "updated_at": now
            }
        )

        if result.rowcount == 0:
            raise NotFoundError(
                "Invoice tidak ditemukan atau sudah tidak aktif"
            )

        # ====================== 2. CLOSE INVOICE STAGE HISTORY ====================== #

        close_history_query = text("""
            UPDATE work_stage_histories
            SET
                ended_at = :ended_at
            WHERE
                id_work_item = :id_work_item
                AND stage = 'INVOICE'
                AND ended_at IS NULL
                AND is_active = 1
        """)

        conn.execute(
            close_history_query,
            {
                "id_work_item": id_work_item,
                "ended_at": now
            }
        )

        # ======================== 3. ROLLBACK WORK ITEM TO BA ======================= #

        update_work_query = text("""
            UPDATE work_items
            SET
                current_stage = 'BA',
                updated_by = :updated_by,
                updated_at = :updated_at
            WHERE
                id_work_item = :id_work_item
                AND is_active = 1
        """)

        conn.execute(
            update_work_query,
            {
                "id_work_item": id_work_item,
                "updated_by": updated_by,
                "updated_at": now
            }
        )

        # ====================== 4. CREATE NEW BA STAGE HISTORY ====================== #

        insert_history_query = text("""
            INSERT INTO work_stage_histories (
                id_work_item, stage, started_at, ended_at, notes, is_active, created_by, created_at
            )
            VALUES (
                :id_work_item, 'BA', :started_at, NULL, :notes, 1, :created_by, :created_at
            )
        """)

        conn.execute(
            insert_history_query,
            {
                "id_work_item": id_work_item,
                "started_at": now,
                "notes": "Stage kembali ke BA setelah invoice dihapus.",
                "created_by": updated_by,
                "created_at": now
            }
        )

    return {
        "id_invoice": id_invoice,
        "id_work_item": id_work_item,
        "current_stage": "BA"
    }
