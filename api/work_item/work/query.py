from sqlalchemy import text

from api.utils.config import engine
from api.shared.helper import get_wita


# ========================= #ANCHOR - HELPER FUNCTION ========================= #

def get_client_by_id(id_client: int):

    sql = text("""
        SELECT
            id_client, code, name, address, phone, email, is_active
        FROM client
        WHERE
            id_client = :id_client
            AND is_active = 1
        LIMIT 1
    """)

    with engine.connect() as conn:
        return conn.execute(
            sql,
            {"id_client": id_client}
        ).mappings().first()


def get_client_pic_by_id(id_client_pic: int):

    sql = text("""
        SELECT
            id_client_pic, id_client, name, position, phone, email, is_active
        FROM client_pic
        WHERE
            id_client_pic = :id_client_pic
            AND is_active = 1
        LIMIT 1
    """)

    with engine.connect() as conn:
        return conn.execute(
            sql,
            {"id_client_pic": id_client_pic}
        ).mappings().first()


def get_work_item_by_id(id_work_item):

    sql = text("""
        SELECT
            id_work_item, work_number, work_name, work_type, id_client, id_client_pic, internal_pic_name, 
            current_stage, progress_percent, start_date, target_end_date, completion_date, notes, 
            is_active, created_by, created_at, updated_by, updated_at
        FROM work_items
        WHERE
            id_work_item = :id_work_item
            AND is_active = 1
        LIMIT 1
    """)

    with engine.connect() as conn:

        return conn.execute(
            sql,
            {
                "id_work_item": id_work_item
            }
        ).mappings().first()

# ============================================================================ #
#                         #SECTION - WORK ITEM                                 #
# ============================================================================ #

def get_work_item_list(search=None, work_type=None, current_stage=None, id_client=None, page=1, per_page=10):

    conditions = [
        "wi.is_active = 1"
    ]

    params = {}

    if search:
        conditions.append("""
            (
                wi.work_number ILIKE :search
                OR wi.work_name ILIKE :search
            )
        """)

        params["search"] = f"%{search.strip()}%"

    if work_type:
        conditions.append("wi.work_type = :work_type")
        params["work_type"] = work_type

    if current_stage:
        conditions.append("wi.current_stage = :current_stage")
        params["current_stage"] = current_stage

    if id_client:
        conditions.append("wi.id_client = :id_client")
        params["id_client"] = id_client

    where_clause = " AND ".join(conditions)

    offset = (page - 1) * per_page

    params["limit"] = per_page
    params["offset"] = offset

    sql = text(f"""
        SELECT
            wi.id_work_item, wi.work_number, wi.work_name, wi.work_type, wi.id_client, c.code AS client_code, 
            c.name AS client_name, wi.id_client_pic, cp.name AS client_pic_name, wi.internal_pic_name, wi.current_stage, 
            wi.progress_percent, wi.start_date, wi.target_end_date, wi.completion_date, wi.notes, 
            wi.created_by, wi.created_at, wi.updated_by, wi.updated_at
        FROM work_items wi
        LEFT JOIN client c
            ON c.id_client = wi.id_client
        LEFT JOIN client_pic cp
            ON cp.id_client_pic = wi.id_client_pic
        WHERE {where_clause}
        ORDER BY
            wi.created_at DESC,
            wi.id_work_item DESC
        LIMIT :limit
        OFFSET :offset
    """)

    sql_count = text(f"""
        SELECT COUNT(*) AS total
        FROM work_items wi

        WHERE {where_clause}
    """)

    with engine.connect() as conn:

        result = conn.execute(
            sql,
            params
        ).mappings().all()

        total = conn.execute(
            sql_count,
            params
        ).scalar()

        return {
            "items": result,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "total_pages": (
                    (total + per_page - 1) // per_page
                    if total
                    else 0
                )
            }
        }



def get_work_item_by_number(work_number: str):

    sql = text("""
        SELECT
            id_work_item, work_number, work_name
        FROM work_items
        WHERE
            LOWER(work_number) = LOWER(:work_number)
            AND is_active = 1
        LIMIT 1
    """)

    with engine.connect() as conn:
        return conn.execute(
            sql,
            {
                "work_number": work_number
            }
        ).mappings().first()


def create_work_item(body: dict):

    sql_work_item = text("""
        INSERT INTO work_items (
            work_number, work_name, work_type, id_client, id_client_pic, internal_pic_name, current_stage, 
            progress_percent, start_date, target_end_date, notes, is_active, created_by, created_at, updated_at
        )
        VALUES (
            :work_number, :work_name, :work_type, :id_client, :id_client_pic, :internal_pic_name, 'IDENTIFIED', 
            :progress_percent, :start_date, :target_end_date, :notes, 1, :created_by, :now, :now
        )
        RETURNING id_work_item
    """)

    sql_stage_history = text("""
        INSERT INTO work_stage_histories (
            id_work_item, stage, started_at, ended_at, notes, is_active, created_by, created_at
        )
        VALUES (
            :id_work_item, 'IDENTIFIED', :now, NULL, NULL, 1, :created_by, :now
        )
    """)

    now = get_wita()

    with engine.begin() as conn:

        result = conn.execute(
            sql_work_item,
            {
                "work_number": body["work_number"].strip(),
                "work_name": body["work_name"].strip(),
                "work_type": body["work_type"],
                "id_client": body["id_client"],
                "id_client_pic": body.get("id_client_pic"),
                "internal_pic_name": (
                    body["internal_pic_name"].strip()
                    if body.get("internal_pic_name")
                    else None
                ),
                "progress_percent": (
                    body.get("progress_percent")
                    if body.get("progress_percent") is not None
                    else 0
                ),
                "start_date": body.get("start_date"),
                "target_end_date": body.get("target_end_date"),
                "notes": body.get("notes"),
                "created_by": body["created_by"],
                "now": now
            }
        )

        id_work_item = result.scalar()

        conn.execute(
            sql_stage_history,
            {
                "id_work_item": id_work_item,
                "created_by": body["created_by"],
                "now": now
            }
        )

        return id_work_item



def get_work_item_detail(id_work_item):

    sql_work = text("""
        SELECT
            wi.id_work_item, wi.work_number, wi.work_name, wi.work_type, wi.id_client, c.code AS client_code, 
            c.name AS client_name, wi.id_client_pic, cp.name AS client_pic_name, cp.position AS client_pic_position, 
            cp.phone AS client_pic_phone, cp.email AS client_pic_email, wi.internal_pic_name, wi.current_stage, 
            wi.progress_percent, wi.start_date, wi.target_end_date, wi.completion_date, wi.notes, wi.is_active, 
            wi.created_by, wi.created_at, wi.updated_by, wi.updated_at
        FROM work_items wi
        LEFT JOIN client c
            ON c.id_client = wi.id_client
        LEFT JOIN client_pic cp
            ON cp.id_client_pic = wi.id_client_pic
        WHERE
            wi.id_work_item = :id_work_item
            AND wi.is_active = 1
        LIMIT 1
    """)

    sql_proposal = text("""
        SELECT
            id_proposal, id_work_item, proposal_number, proposal_date, proposal_value, valid_until, status, notes, 
            created_by, created_at, updated_by, updated_at
        FROM work_proposals
        WHERE
            id_work_item = :id_work_item
            AND is_active = 1
        ORDER BY proposal_date DESC, id_proposal DESC
    """)

    sql_contract = text("""
        SELECT
            id_contract, id_work_item, contract_number, contract_date, start_date, end_date, contract_value, vat_rate, 
            status, notes, created_by, created_at, updated_by, updated_at
        FROM work_contracts
        WHERE
            id_work_item = :id_work_item
            AND is_active = 1
        ORDER BY contract_date DESC, id_contract DESC
    """)

    sql_completion = text("""
        SELECT
            id_completion, id_work_item, ba_number, ba_date, completion_date, document_url, notes, 
            created_by, created_at, updated_by, updated_at
        FROM work_completions
        WHERE
            id_work_item = :id_work_item
            AND is_active = 1
        LIMIT 1
    """)

    sql_invoice = text("""
        SELECT
            id_invoice, id_work_item, id_completion, invoice_number, invoice_date, invoice_value, vat_rate, due_date, 
            document_url, notes, created_by, created_at, updated_by, updated_at
        FROM work_invoices
        WHERE
            id_work_item = :id_work_item
            AND is_active = 1
        ORDER BY invoice_date DESC, id_invoice DESC
    """)

    sql_payment = text("""
        SELECT
            p.id_payment, p.id_invoice, p.payment_date, p.amount, p.document_url, p.notes, 
            p.created_by, p.created_at, p.updated_by, p.updated_at
        FROM work_payments p
        INNER JOIN work_invoices i
            ON i.id_invoice = p.id_invoice
        WHERE
            i.id_work_item = :id_work_item
            AND p.is_active = 1
            AND i.is_active = 1
        ORDER BY
            p.payment_date DESC,
            p.id_payment DESC
    """)

    sql_stage_history = text("""
        SELECT
            id_stage_history, id_work_item, stage, started_at, ended_at, notes, created_by, created_at
        FROM work_stage_histories
        WHERE
            id_work_item = :id_work_item
            AND is_active = 1
        ORDER BY
            started_at ASC,
            id_stage_history ASC
    """)

    sql_progress_history = text("""
        SELECT
            id_progress_history, id_work_item, progress_percent, progress_date, notes, created_by, created_at
        FROM work_progress_histories
        WHERE
            id_work_item = :id_work_item
            AND is_active = 1
        ORDER BY
            progress_date ASC,
            id_progress_history ASC
    """)

    with engine.connect() as conn:

        work_item = conn.execute(
            sql_work,
            {
                "id_work_item": id_work_item
            }
        ).mappings().first()

        if not work_item:
            return None

        proposals = conn.execute(
            sql_proposal,
            {
                "id_work_item": id_work_item
            }
        ).mappings().all()

        contracts = conn.execute(
            sql_contract,
            {
                "id_work_item": id_work_item
            }
        ).mappings().all()

        completion = conn.execute(
            sql_completion,
            {
                "id_work_item": id_work_item
            }
        ).mappings().first()

        invoices = conn.execute(
            sql_invoice,
            {
                "id_work_item": id_work_item
            }
        ).mappings().all()

        payments = conn.execute(
            sql_payment,
            {
                "id_work_item": id_work_item
            }
        ).mappings().all()

        stage_histories = conn.execute(
            sql_stage_history,
            {
                "id_work_item": id_work_item
            }
        ).mappings().all()

        progress_histories = conn.execute(
            sql_progress_history,
            {
                "id_work_item": id_work_item
            }
        ).mappings().all()

        return {
            "work_item": work_item,
            "proposals": proposals,
            "contracts": contracts,
            "completion": completion,
            "invoices": invoices,
            "payments": payments,
            "stage_histories": stage_histories,
            "progress_histories": progress_histories
        }


def update_work_item(id_work_item, body):

    sql = text("""
        UPDATE work_items
        SET
            work_number = :work_number,
            work_name = :work_name,
            work_type = :work_type,
            id_client = :id_client,
            id_client_pic = :id_client_pic,
            internal_pic_name = :internal_pic_name,
            start_date = :start_date,
            target_end_date = :target_end_date,
            notes = :notes,
            updated_by = :updated_by,
            updated_at = :updated_at
        WHERE
            id_work_item = :id_work_item
            AND is_active = 1
    """)

    now = get_wita()

    with engine.begin() as conn:

        conn.execute(
            sql,
            {
                "id_work_item": id_work_item,
                "work_number": body["work_number"].strip(),
                "work_name": body["work_name"].strip(),
                "work_type": body["work_type"],
                "id_client": body["id_client"],
                "id_client_pic": body.get("id_client_pic"),
                "internal_pic_name": (
                    body["internal_pic_name"].strip()
                    if body.get("internal_pic_name")
                    else None
                ),
                "start_date": body.get("start_date"),
                "target_end_date": body.get("target_end_date"),
                "notes": body.get("notes"),
                "updated_by": body["updated_by"],
                "updated_at": now
            }
        )


def delete_work_item(id_work_item, updated_by):

    sql = text("""
        UPDATE work_items
        SET
            is_active = 0,
            updated_by = :updated_by,
            updated_at = :updated_at
        WHERE
            id_work_item = :id_work_item
            AND is_active = 1
    """)

    now = get_wita()

    with engine.begin() as conn:

        conn.execute(
            sql,
            {
                "id_work_item": id_work_item,
                "updated_by": updated_by,
                "updated_at": now
            }
        )


def get_work_item_options(context=None):

    table_mapping = {
        "quotation": "work_proposals",
        "contract": "work_contracts",
        "invoice": "work_invoices",
        "completion": "work_completions"
    }

    query = """
        SELECT
            wi.id_work_item AS id,
            CONCAT(wi.work_number, ' - ', wi.work_name) AS label
        FROM work_items wi
        WHERE wi.is_active = 1
    """

    params = {}

    if context:
        table_name = table_mapping[context]

        query += f"""
            AND NOT EXISTS (
                SELECT 1
                FROM {table_name} wt
                WHERE wt.id_work_item = wi.id_work_item
                  AND wt.is_active = 1
            )
        """

    query += """
        ORDER BY wi.work_number ASC
    """

    with engine.connect() as conn:
        result = conn.execute(
            text(query),
            params
        ).mappings().all()

    return [dict(row) for row in result]