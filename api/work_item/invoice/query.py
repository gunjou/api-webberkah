from sqlalchemy import text

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

def get_invoice_list(search=None, id_work_item=None, id_completion=None, page=1, per_page=10):

    offset = (page - 1) * per_page

    conditions = [
        "wi.is_active = 1",
        "wi2.is_active = 1"
    ]

    params = {
        "limit": per_page,
        "offset": offset
    }

    # ============================================================
    # FILTER SEARCH
    # ============================================================

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

    # ============================================================
    # FILTER WORK ITEM
    # ============================================================

    if id_work_item:
        conditions.append(
            "wi2.id_work_item = :id_work_item"
        )

        params["id_work_item"] = id_work_item

    # ============================================================
    # FILTER COMPLETION / BA
    # ============================================================

    if id_completion:
        conditions.append(
            "wi2.id_completion = :id_completion"
        )

        params["id_completion"] = id_completion

    where_clause = " AND ".join(conditions)

    # ============================================================
    # DATA QUERY
    # ============================================================

    query = text(f"""
        SELECT
            wi2.id_invoice, wi2.id_work_item, wi.work_number, wi.work_name, wi.work_type, wi.id_client, 
            c.code AS client_code, c.name AS client_name, wi2.id_completion, wc.ba_number, wi2.invoice_number, 
            wi2.invoice_date, wi2.invoice_value, wi2.vat_rate, wi2.due_date, wi2.document_url, wi2.notes,
            wi2.is_active, wi2.created_by, wi2.created_at, wi2.updated_by, wi2.updated_at
        FROM work_invoices wi2
        INNER JOIN work_items wi
            ON wi.id_work_item = wi2.id_work_item
        LEFT JOIN client c
            ON c.id_client = wi.id_client
        LEFT JOIN work_completions wc
            ON wc.id_completion = wi2.id_completion
           AND wc.is_active = 1
        WHERE {where_clause}
        ORDER BY
            wi2.invoice_date DESC,
            wi2.id_invoice DESC
        LIMIT :limit
        OFFSET :offset
    """)

    # ============================================================
    # COUNT QUERY
    # ============================================================

    count_query = text(f"""
        SELECT COUNT(*)
        FROM work_invoices wi2
        INNER JOIN work_items wi
            ON wi.id_work_item = wi2.id_work_item
        LEFT JOIN client c
            ON c.id_client = wi.id_client
        LEFT JOIN work_completions wc
            ON wc.id_completion = wi2.id_completion
           AND wc.is_active = 1
        WHERE {where_clause}
    """)

    # ============================================================
    # EXECUTE
    # ============================================================

    with engine.connect() as conn:

        result = conn.execute(
            query,
            params
        ).mappings().all()

        total = conn.execute(
            count_query,
            params
        ).scalar()

    return {
        "items": [dict(row) for row in result],
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": (
                (total + per_page - 1) // per_page
            )
        }
    }


def create_invoice(id_work_item, id_completion, invoice_number, invoice_date, invoice_value, vat_rate, due_date, document_url, notes, created_by):

    query = text("""
        INSERT INTO work_invoices (
            id_work_item, id_completion, invoice_number, invoice_date, invoice_value, vat_rate, due_date, 
            document_url, notes, is_active, created_by, created_at
        )
        VALUES (
            :id_work_item, :id_completion, :invoice_number, :invoice_date, :invoice_value, :vat_rate, :due_date, 
            :document_url, :notes, 1, :created_by, :created_at
        )
        RETURNING
            id_invoice, id_work_item, id_completion, invoice_number, invoice_date, invoice_value, vat_rate, due_date, 
            document_url, notes, is_active, created_by, created_at
    """)

    with engine.begin() as conn:

        result = conn.execute(
            query,
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
                "created_at": get_wita()
            }
        ).mappings().first()

    return dict(result)


def get_invoice_detail(id_invoice):

    query = text("""
        SELECT
            wi2.id_invoice, wi2.id_work_item,

            -- Work Item
            wi.work_number, wi.work_name, wi.work_type, wi.current_stage, wi.progress_percent, wi.start_date, wi.target_end_date,

            -- Client
            wi.id_client, c.code AS client_code, c.name AS client_name,

            -- Client PIC
            wi.id_client_pic, cp.name AS client_pic_name, cp.position AS client_pic_position, 
            cp.phone AS client_pic_phone, cp.email AS client_pic_email,

            -- Internal PIC
            wi.internal_pic_name,

            -- BA
            wi2.id_completion, wc.ba_number, wc.ba_date, wc.completion_date,

            -- Invoice
            wi2.invoice_number, wi2.invoice_date, wi2.invoice_value, wi2.vat_rate, wi2.due_date, wi2.document_url, wi2.notes,

            -- Audit
            wi2.is_active, wi2.created_by, wi2.created_at, wi2.updated_by, wi2.updated_at
        FROM work_invoices wi2
        INNER JOIN work_items wi
            ON wi.id_work_item = wi2.id_work_item
        LEFT JOIN client c
            ON c.id_client = wi.id_client
        LEFT JOIN client_pic cp
            ON cp.id_client_pic = wi.id_client_pic
        LEFT JOIN work_completions wc
            ON wc.id_completion = wi2.id_completion
           AND wc.is_active = 1
        WHERE wi2.id_invoice = :id_invoice
          AND wi2.is_active = 1
    """)

    with engine.connect() as conn:

        result = conn.execute(
            query,
            {
                "id_invoice": id_invoice
            }
        ).mappings().first()

    return dict(result) if result else None


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


def delete_invoice(id_invoice, updated_by):

    query = text("""
        UPDATE work_invoices
        SET
            is_active = 0,
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
                "updated_by": updated_by,
                "updated_at": get_wita()
            }
        )