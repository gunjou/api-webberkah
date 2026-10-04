from sqlalchemy import text

from api.utils.config import engine
from api.shared.helper import get_wita


# ========================= #ANCHOR - HELPER FUNCTION ========================= #

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


def get_completion_by_work_item(id_work_item, exclude_id=None):

    query = text("""
        SELECT
            id_completion, id_work_item, ba_number
        FROM work_completions
        WHERE id_work_item = :id_work_item
          AND is_active = 1
          AND (
              :exclude_id IS NULL
              OR id_completion != :exclude_id
          )
        LIMIT 1
    """)

    with engine.connect() as conn:

        result = conn.execute(
            query,
            {
                "id_work_item": id_work_item,
                "exclude_id": exclude_id
            }
        ).mappings().first()

    return dict(result) if result else None


def get_completion_by_number(ba_number, exclude_id=None):

    query = text("""
        SELECT
            id_completion, id_work_item, ba_number
        FROM work_completions
        WHERE ba_number = :ba_number
          AND is_active = 1
          AND (
              :exclude_id IS NULL
              OR id_completion != :exclude_id
          )
        LIMIT 1
    """)

    with engine.connect() as conn:

        result = conn.execute(
            query,
            {
                "ba_number": ba_number,
                "exclude_id": exclude_id
            }
        ).mappings().first()

    return dict(result) if result else None


def get_completion_by_id(id_completion):

    query = text("""
        SELECT
            id_completion, id_work_item, ba_number, ba_date, completion_date, document_url, notes, is_active
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

# ============================================================================ #
#                           #SECTION - COMPLETION (BA)                         #
# ============================================================================ #

def get_completion_list(filters):

    search = filters.get("search")
    id_work_item = filters.get("id_work_item")

    page = filters.get("page", 1)
    per_page = filters.get("per_page", 10)

    offset = (page - 1) * per_page

    conditions = [
        "wc.is_active = 1"
    ]

    params = {
        "limit": per_page,
        "offset": offset
    }

    if search:
        conditions.append("""
            (
                LOWER(wc.ba_number) LIKE LOWER(:search)
                OR LOWER(wi.work_number) LIKE LOWER(:search)
                OR LOWER(wi.work_name) LIKE LOWER(:search)
                OR LOWER(c.name) LIKE LOWER(:search)
            )
        """)

        params["search"] = f"%{search.strip()}%"

    if id_work_item:
        conditions.append(
            "wc.id_work_item = :id_work_item"
        )

        params["id_work_item"] = id_work_item

    where_clause = " AND ".join(conditions)

    count_query = text(f"""
        SELECT COUNT(*)
        FROM work_completions wc

        INNER JOIN work_items wi
            ON wi.id_work_item = wc.id_work_item

        LEFT JOIN client c
            ON c.id_client = wi.id_client

        WHERE {where_clause}
    """)

    query = text(f"""
        SELECT
            wc.id_completion, wc.id_work_item, wi.work_number, wi.work_name, wi.work_type, wi.id_client, 
            c.code AS client_code, c.name AS client_name, wc.ba_number, wc.ba_date, wc.completion_date, wc.document_url, 
            wc.notes, wc.created_by, wc.created_at, wc.updated_by, wc.updated_at
        FROM work_completions wc
        INNER JOIN work_items wi
            ON wi.id_work_item = wc.id_work_item
        LEFT JOIN client c
            ON c.id_client = wi.id_client
        WHERE {where_clause}
        ORDER BY wc.ba_date DESC, wc.id_completion DESC
        LIMIT :limit
        OFFSET :offset
    """)

    with engine.connect() as conn:

        total = conn.execute(
            count_query,
            params
        ).scalar()

        result = conn.execute(
            query,
            params
        ).mappings().all()

    return {
        "items": [dict(row) for row in result],
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": (
                (total + per_page - 1) // per_page
                if total > 0 else 0
            )
        }
    }


def create_completion(id_work_item, ba_number, ba_date, completion_date, document_url, notes, created_by):

    query = text("""
        INSERT INTO work_completions (
            id_work_item, ba_number, ba_date, completion_date, document_url, notes, 
            is_active, created_by, created_at
        )
        VALUES (
            :id_work_item, :ba_number, :ba_date, :completion_date, :document_url, :notes, 
            1, :created_by, :created_at
        )
        RETURNING
            id_completion
    """)

    with engine.begin() as conn:

        result = conn.execute(
            query,
            {
                "id_work_item": id_work_item,
                "ba_number": ba_number,
                "ba_date": ba_date,
                "completion_date": completion_date,
                "document_url": document_url,
                "notes": notes,
                "created_by": created_by,
                "created_at": get_wita()
            }
        ).mappings().first()

    return dict(result)


def get_completion_detail(id_completion):

    query = text("""
        SELECT
            wc.id_completion, wc.id_work_item, wi.work_number, wi.work_name, wi.work_type, wi.current_stage, 
            wi.progress_percent, wi.id_client, c.code AS client_code, c.name AS client_name, wi.id_client_pic, 
            cp.name AS client_pic_name, cp.position AS client_pic_position, cp.phone AS client_pic_phone, 
            cp.email AS client_pic_email, wi.internal_pic_name, wc.ba_number, wc.ba_date, wc.completion_date, 
            wc.document_url, wc.notes, wc.is_active, wc.created_by, wc.created_at, wc.updated_by, wc.updated_at
        FROM work_completions wc
        INNER JOIN work_items wi
            ON wi.id_work_item = wc.id_work_item
        LEFT JOIN client c
            ON c.id_client = wi.id_client
        LEFT JOIN client_pic cp
            ON cp.id_client_pic = wi.id_client_pic
        WHERE wc.id_completion = :id_completion
          AND wc.is_active = 1
    """)

    with engine.connect() as conn:

        result = conn.execute(
            query,
            {
                "id_completion": id_completion
            }
        ).mappings().first()

    return dict(result) if result else None


def update_completion(id_completion, id_work_item, ba_number, ba_date, completion_date, document_url, notes, updated_by):

    query = text("""
        UPDATE work_completions
        SET
            id_work_item = :id_work_item,
            ba_number = :ba_number,
            ba_date = :ba_date,
            completion_date = :completion_date,
            document_url = :document_url,
            notes = :notes,
            updated_by = :updated_by,
            updated_at = :updated_at
        WHERE id_completion = :id_completion
          AND is_active = 1
    """)

    with engine.begin() as conn:

        conn.execute(
            query,
            {
                "id_completion": id_completion,
                "id_work_item": id_work_item,
                "ba_number": ba_number,
                "ba_date": ba_date,
                "completion_date": completion_date,
                "document_url": document_url,
                "notes": notes,
                "updated_by": updated_by,
                "updated_at": get_wita()
            }
        )


def delete_completion(id_completion, updated_by):

    query = text("""
        UPDATE work_completions
        SET
            is_active = 0,
            updated_by = :updated_by,
            updated_at = :updated_at
        WHERE id_completion = :id_completion
          AND is_active = 1
    """)

    with engine.begin() as conn:

        conn.execute(
            query,
            {
                "id_completion": id_completion,
                "updated_by": updated_by,
                "updated_at": get_wita()
            }
        )


def get_completion_options(context=None):

    query = """
        SELECT
            wc.id_completion AS id,
            CONCAT(
                wc.ba_number,
                ' - ',
                wi.work_number,
                ' - ',
                wi.work_name
            ) AS label
        FROM work_completions wc
        INNER JOIN work_items wi
            ON wi.id_work_item = wc.id_work_item
        WHERE wc.is_active = 1
          AND wi.is_active = 1
    """

    params = {}

    if context == "invoice":

        query += """
            AND NOT EXISTS (
                SELECT 1
                FROM work_invoices inv
                WHERE inv.id_completion = wc.id_completion
                  AND inv.is_active = 1
            )
        """

    query += """
        ORDER BY
            wc.ba_date DESC,
            wc.id_completion DESC
    """

    with engine.connect() as conn:

        result = conn.execute(
            text(query),
            params
        ).mappings().all()

    return [dict(row) for row in result]