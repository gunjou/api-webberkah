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


def get_contract_by_number(contract_number, exclude_id=None):

    query = text("""
        SELECT
            id_contract,
            contract_number
        FROM work_contracts
        WHERE LOWER(contract_number) = LOWER(:contract_number)
          AND is_active = 1
          AND (
              :exclude_id IS NULL
              OR id_contract != :exclude_id
          )
        LIMIT 1
    """)

    with engine.connect() as conn:

        result = conn.execute(
            query,
            {
                "contract_number": contract_number.strip(),
                "exclude_id": exclude_id
            }
        ).mappings().first()

    return dict(result) if result else None


def get_contract_by_id(id_contract):

    query = text("""
        SELECT
            id_contract, id_work_item, contract_number, contract_date, start_date, end_date, contract_value, vat_rate, 
            status, notes, is_active, created_by, created_at, updated_by, updated_at
        FROM work_contracts
        WHERE id_contract = :id_contract
          AND is_active = 1
    """)

    with engine.connect() as conn:

        result = conn.execute(
            query,
            {
                "id_contract": id_contract
            }
        ).mappings().first()

    return dict(result) if result else None


# ============================================================================ #
#                              #SECTION - CONTRACT                             #
# ============================================================================ #

def get_contract_list(filters):

    search = filters.get("search")
    status = filters.get("status")
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
                LOWER(wc.contract_number) LIKE LOWER(:search)
                OR LOWER(wi.work_number) LIKE LOWER(:search)
                OR LOWER(wi.work_name) LIKE LOWER(:search)
                OR LOWER(c.name) LIKE LOWER(:search)
            )
        """)

        params["search"] = f"%{search.strip()}%"

    if status:
        conditions.append(
            "wc.status = :status"
        )

        params["status"] = status

    if id_work_item:
        conditions.append(
            "wc.id_work_item = :id_work_item"
        )

        params["id_work_item"] = id_work_item

    where_clause = " AND ".join(conditions)

    count_query = text(f"""
        SELECT COUNT(*)
        FROM work_contracts wc
        INNER JOIN work_items wi
            ON wi.id_work_item = wc.id_work_item
        LEFT JOIN client c
            ON c.id_client = wi.id_client
        WHERE {where_clause}
    """)

    query = text(f"""
        SELECT
            wc.id_contract, wc.id_work_item, wi.work_number, wi.work_name, wi.work_type, wi.id_client, c.code AS client_code, 
            c.name AS client_name, wi.id_client_pic, cp.name AS client_pic_name, wc.contract_number, wc.contract_date, 
            wc.start_date, wc.end_date, wc.contract_value, wc.vat_rate, wc.status, wc.notes, 
            wc.created_by, wc.created_at, wc.updated_by, wc.updated_at
        FROM work_contracts wc
        INNER JOIN work_items wi
            ON wi.id_work_item = wc.id_work_item
        LEFT JOIN client c
            ON c.id_client = wi.id_client
        LEFT JOIN client_pic cp
            ON cp.id_client_pic = wi.id_client_pic
        WHERE {where_clause}
        ORDER BY wc.contract_date DESC, wc.id_contract DESC
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


def create_contract(id_work_item, contract_number, contract_date, start_date, end_date, contract_value, vat_rate, status, notes, created_by):

    query = text("""
        INSERT INTO work_contracts (
            id_work_item, contract_number, contract_date, start_date, end_date, contract_value, vat_rate, 
            status, notes, is_active, created_by, created_at
        )
        VALUES (
            :id_work_item, :contract_number, :contract_date, :start_date, :end_date, :contract_value, :vat_rate, 
            :status, :notes, 1, :created_by, :created_at
        )
        RETURNING
            id_contract
    """)

    with engine.begin() as conn:

        result = conn.execute(
            query,
            {
                "id_work_item": id_work_item,
                "contract_number": contract_number,
                "contract_date": contract_date,
                "start_date": start_date,
                "end_date": end_date,
                "contract_value": contract_value,
                "vat_rate": vat_rate,
                "status": status,
                "notes": notes,
                "created_by": created_by,
                "created_at": get_wita()
            }
        ).mappings().first()

    return dict(result)


def get_contract_detail(id_contract):

    query = text("""
        SELECT
            wc.id_contract, wc.id_work_item, wi.work_number, wi.work_name, wi.work_type, wi.current_stage, 
            wi.progress_percent, wi.id_client, c.code AS client_code, c.name AS client_name, wi.id_client_pic, 
            cp.name AS client_pic_name, cp.position AS client_pic_position, cp.phone AS client_pic_phone, 
            cp.email AS client_pic_email, wc.contract_number, wc.contract_date, wc.start_date, wc.end_date, 
            wc.contract_value, wc.vat_rate, wc.status, wc.notes, 
            wc.is_active, wc.created_by, wc.created_at, wc.updated_by, wc.updated_at
        FROM work_contracts wc
        INNER JOIN work_items wi
            ON wi.id_work_item = wc.id_work_item
        LEFT JOIN client c
            ON c.id_client = wi.id_client
        LEFT JOIN client_pic cp
            ON cp.id_client_pic = wi.id_client_pic
        WHERE wc.id_contract = :id_contract
          AND wc.is_active = 1
    """)

    with engine.connect() as conn:

        result = conn.execute(
            query,
            {
                "id_contract": id_contract
            }
        ).mappings().first()

    return dict(result) if result else None


def update_contract(id_contract, id_work_item, contract_number, contract_date, start_date, end_date, contract_value, vat_rate, status, notes, updated_by):

    query = text("""
        UPDATE work_contracts
        SET
            id_work_item = :id_work_item,
            contract_number = :contract_number,
            contract_date = :contract_date,
            start_date = :start_date,
            end_date = :end_date,
            contract_value = :contract_value,
            vat_rate = :vat_rate,
            status = :status,
            notes = :notes,
            updated_by = :updated_by,
            updated_at = :updated_at
        WHERE id_contract = :id_contract
          AND is_active = 1
        RETURNING
            id_contract, id_work_item, contract_number, contract_date, start_date, end_date, contract_value, vat_rate, 
            status, notes, updated_by, updated_at
    """)

    with engine.begin() as conn:

        result = conn.execute(
            query,
            {
                "id_contract": id_contract,
                "id_work_item": id_work_item,
                "contract_number": contract_number,
                "contract_date": contract_date,
                "start_date": start_date,
                "end_date": end_date,
                "contract_value": contract_value,
                "vat_rate": vat_rate,
                "status": status,
                "notes": notes,
                "updated_by": updated_by,
                "updated_at": get_wita()
            }
        ).mappings().first()

    return dict(result) if result else None


def delete_contract(id_contract, updated_by):

    query = text("""
        UPDATE work_contracts
        SET
            is_active = 0,
            updated_by = :updated_by,
            updated_at = :updated_at
        WHERE id_contract = :id_contract
          AND is_active = 1
    """)

    with engine.begin() as conn:

        conn.execute(
            query,
            {
                "id_contract": id_contract,
                "updated_by": updated_by,
                "updated_at": get_wita()
            }
        )