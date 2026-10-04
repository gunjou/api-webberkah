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


def get_quotation_by_number(proposal_number, exclude_id=None):

    query = text("""
        SELECT
            id_proposal, proposal_number
        FROM work_proposals
        WHERE LOWER(proposal_number) = LOWER(:proposal_number)
          AND is_active = 1
          AND (
              :exclude_id IS NULL
              OR id_proposal != :exclude_id
          )
        LIMIT 1
    """)

    with engine.connect() as conn:

        result = conn.execute(
            query,
            {
                "proposal_number": proposal_number.strip(),
                "exclude_id": exclude_id
            }
        ).mappings().first()

    return dict(result) if result else None


def get_quotation_by_id(id_proposal):

    query = text("""
        SELECT
            id_proposal, id_work_item, proposal_number, proposal_date, proposal_value, valid_until, 
            status, notes, is_active, created_by, created_at, updated_by, updated_at
        FROM work_proposals
        WHERE id_proposal = :id_proposal
          AND is_active = 1
    """)

    with engine.connect() as conn:

        result = conn.execute(
            query,
            {
                "id_proposal": id_proposal
            }
        ).mappings().first()

    return dict(result) if result else None

# ============================================================================ #
#                         #SECTION - QUOTATION                                 #
# ============================================================================ #

def get_quotation_list(search=None, status=None, id_work_item=None, page=1, per_page=10):

    conditions = ["wp.is_active = 1"]

    params = {}

    # ---------------------------------------------------------------------- #
    # Search
    # ---------------------------------------------------------------------- #

    if search:
        conditions.append("""wp.proposal_number ILIKE :search""")
        params["search"] = f"%{search.strip()}%"

    # ---------------------------------------------------------------------- #
    # Status
    # ---------------------------------------------------------------------- #

    if status:
        conditions.append("wp.status = :status")
        params["status"] = status

    # ---------------------------------------------------------------------- #
    # Work Item
    # ---------------------------------------------------------------------- #

    if id_work_item:
        conditions.append("wp.id_work_item = :id_work_item")
        params["id_work_item"] = id_work_item

    where_clause = " AND ".join(conditions)

    offset = (page - 1) * per_page

    params["limit"] = per_page
    params["offset"] = offset

    sql = text(f"""
        SELECT
            wp.id_proposal, wp.id_work_item, wi.work_number, wi.work_name, c.code AS client_code, c.name AS client_name, 
            wi.id_client_pic, cp.name AS client_pic_name, wp.proposal_number, wp.proposal_date, wp.proposal_value, 
            wp.valid_until, wp.status, wp.notes, wp.created_by, wp.created_at, wp.updated_by, wp.updated_at
        FROM work_proposals wp
        INNER JOIN work_items wi
            ON wi.id_work_item = wp.id_work_item
        LEFT JOIN client c
            ON c.id_client = wi.id_client
        LEFT JOIN client_pic cp
            ON cp.id_client_pic = wi.id_client_pic
        WHERE {where_clause}
        ORDER BY
            wp.proposal_date DESC,
            wp.id_proposal DESC
        LIMIT :limit
        OFFSET :offset
    """)

    sql_count = text(f"""
        SELECT COUNT(*) AS total
        FROM work_proposals wp
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


def create_quotation(body: dict):

    sql = text("""
        INSERT INTO work_proposals (
            id_work_item, proposal_number, proposal_date, proposal_value, valid_until, status, notes, 
            is_active, created_by, created_at, updated_at
        )
        VALUES (
            :id_work_item, :proposal_number, :proposal_date, :proposal_value, :valid_until, :status, :notes, 
            1, :created_by, :now, :now
        )
        RETURNING id_proposal
    """)

    now = get_wita()

    with engine.begin() as conn:

        result = conn.execute(
            sql,
            {
                "id_work_item": body["id_work_item"],
                "proposal_number": body["proposal_number"].strip(),
                "proposal_date": body["proposal_date"],
                "proposal_value": body.get("proposal_value"),
                "valid_until": body.get("valid_until"),
                "status": body["status"],
                "notes": body.get("notes"),
                "created_by": body["created_by"],
                "now": now
            }
        )

        return result.scalar()


def get_quotation_detail(id_proposal):

    query = text("""
        SELECT
            wp.id_proposal, wp.id_work_item, wi.work_number, wi.work_name, wi.work_type, wi.id_client, 
            c.code AS client_code, c.name AS client_name, wi.id_client_pic, cp.name AS client_pic_name, 
            cp.position AS client_pic_position, cp.phone AS client_pic_phone, cp.email AS client_pic_email, 
            wp.proposal_number, wp.proposal_date, wp.proposal_value, wp.valid_until, wp.status, wp.notes, 
            wp.is_active, wp.created_by, wp.created_at, wp.updated_by, wp.updated_at
        FROM work_proposals wp
        INNER JOIN work_items wi
            ON wi.id_work_item = wp.id_work_item
        LEFT JOIN client c
            ON c.id_client = wi.id_client
        LEFT JOIN client_pic cp
            ON cp.id_client_pic = wi.id_client_pic
        WHERE wp.id_proposal = :id_proposal
          AND wp.is_active = 1
    """)

    with engine.connect() as conn:

        result = conn.execute(
            query,
            {
                "id_proposal": id_proposal
            }
        ).mappings().first()

    return dict(result) if result else None


def update_quotation(id_proposal, id_work_item, proposal_number, proposal_date, proposal_value, valid_until, status, notes, updated_by):

    query = text("""
        UPDATE work_proposals
        SET
            id_work_item = :id_work_item,
            proposal_number = :proposal_number,
            proposal_date = :proposal_date,
            proposal_value = :proposal_value,
            valid_until = :valid_until,
            status = :status,
            notes = :notes,
            updated_by = :updated_by,
            updated_at = :updated_at
        WHERE id_proposal = :id_proposal
          AND is_active = 1
        RETURNING
            id_proposal, id_work_item, proposal_number, proposal_date, proposal_value, valid_until, status, notes, 
            updated_by, updated_at
    """)

    with engine.begin() as conn:

        result = conn.execute(
            query,
            {
                "id_proposal": id_proposal,
                "id_work_item": id_work_item,
                "proposal_number": proposal_number,
                "proposal_date": proposal_date,
                "proposal_value": proposal_value,
                "valid_until": valid_until,
                "status": status,
                "notes": notes,
                "updated_by": updated_by,
                "updated_at": get_wita()
            }
        ).mappings().first()

    return dict(result) if result else None


def delete_quotation(id_proposal, updated_by):

    query = text("""
        UPDATE work_proposals
        SET
            is_active = 0,
            updated_by = :updated_by,
            updated_at = :updated_at
        WHERE id_proposal = :id_proposal
          AND is_active = 1
    """)

    with engine.begin() as conn:

        conn.execute(
            query,
            {
                "id_proposal": id_proposal,
                "updated_by": updated_by,
                "updated_at": get_wita()
            }
        )