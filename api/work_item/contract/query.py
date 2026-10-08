from sqlalchemy import text

from api.shared.exceptions import NotFoundError
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

def get_contract_list(stage="ACTIVE", search=None, status=None, id_work_item=None, id_client=None, page=None, per_page=None):

    conditions = [
        "wc.is_active = 1",
        "wi.is_active = 1"
    ]

    params = {}

    # =================================== Stage ================================== #

    if stage == "ACTIVE":
        conditions.append(
            "wi.current_stage != 'CLOSED'"
        )

    elif stage == "CLOSED":
        conditions.append(
            "wi.current_stage = 'CLOSED'"
        )

    # ================================== Search ================================== #

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

    # ================================== Status ================================== #

    if status:
        conditions.append(
            "wc.status = :status"
        )

        params["status"] = status

    # ================================= Work Item ================================ #

    if id_work_item:
        conditions.append(
            "wc.id_work_item = :id_work_item"
        )

        params["id_work_item"] = id_work_item

    # ================================== Client ================================== #

    if id_client:
        conditions.append(
            "wi.id_client = :id_client"
        )

        params["id_client"] = id_client

    where_clause = " AND ".join(conditions)

    # ================================ Pagination ================================ #

    pagination_clause = ""

    if (
        stage == "CLOSED"
        and page is not None
        and per_page is not None
    ):
        offset = (page - 1) * per_page

        params["limit"] = per_page
        params["offset"] = offset

        pagination_clause = """
            LIMIT :limit
            OFFSET :offset
        """

    # ================================ Count Query =============================== #

    count_query = text(f"""
        SELECT COUNT(*)
        FROM work_contracts wc
        INNER JOIN work_items wi
            ON wi.id_work_item = wc.id_work_item
        LEFT JOIN client c
            ON c.id_client = wi.id_client
        WHERE {where_clause}
    """)

    # ================================ Data Query ================================ #

    query = text(f"""
        SELECT
            wc.id_contract, wc.id_work_item, wi.work_number, wi.work_name, wi.work_type, wi.current_stage AS stage, 
            wi.id_client, c.code AS client_code, c.name AS client_name, wi.id_client_pic, cp.name AS client_pic_name, 
            wc.contract_number, wc.contract_date, wc.start_date, wc.end_date, wc.contract_value, wc.vat_rate, 
            wc.status, wc.notes, wc.created_by, wc.created_at, wc.updated_by, wc.updated_at
        FROM work_contracts wc
        INNER JOIN work_items wi
            ON wi.id_work_item = wc.id_work_item
        LEFT JOIN client c
            ON c.id_client = wi.id_client
        LEFT JOIN client_pic cp
            ON cp.id_client_pic = wi.id_client_pic
        WHERE {where_clause}
        ORDER BY
            wc.contract_date DESC,
            wc.id_contract DESC
        {pagination_clause}
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

    response = {
        "items": [dict(row) for row in result],
        "total": total
    }

    # ============================ Pagination Response =========================== #

    if (
        stage == "CLOSED"
        and page is not None
        and per_page is not None
    ):
        response["pagination"] = {
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": (
                (total + per_page - 1) // per_page
                if total > 0
                else 0
            )
        }

    return response


def create_contract(id_work_item, contract_number, contract_date, start_date, end_date, contract_value, vat_rate, status, notes, created_by):

    now = get_wita()

    with engine.begin() as conn:

        # ------------------------------------------------------------------ #
        # Create Contract
        # ------------------------------------------------------------------ #

        result = conn.execute(
            text("""
                INSERT INTO work_contracts (
                    id_work_item, contract_number, contract_date, start_date, end_date, contract_value, vat_rate, 
                    status, notes, is_active, created_by, created_at, updated_at
                )
                VALUES (
                    :id_work_item, :contract_number, :contract_date, :start_date, :end_date, :contract_value, :vat_rate, 
                    :status, :notes, 1, :created_by, :now, :now
                )
                RETURNING id_contract
            """),
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
                "now": now
            }
        )

        id_contract = result.scalar()

        # ------------------------------------------------------------------ #
        # Close Current Stage History
        # ------------------------------------------------------------------ #

        conn.execute(
            text("""
                UPDATE work_stage_histories
                SET ended_at = :now
                WHERE id_work_item = :id_work_item
                  AND ended_at IS NULL
                  AND is_active = 1
            """),
            {
                "id_work_item": id_work_item,
                "now": now
            }
        )

        # ------------------------------------------------------------------ #
        # Update Work Item Stage
        # ------------------------------------------------------------------ #

        conn.execute(
            text("""
                UPDATE work_items
                SET
                    current_stage = 'CONTRACT',
                    updated_by = :updated_by,
                    updated_at = :now
                WHERE id_work_item = :id_work_item
                  AND is_active = 1
            """),
            {
                "id_work_item": id_work_item,
                "updated_by": created_by,
                "now": now
            }
        )

        # ------------------------------------------------------------------ #
        # Create Stage History
        # ------------------------------------------------------------------ #

        conn.execute(
            text("""
                INSERT INTO work_stage_histories (
                    id_work_item, stage, started_at, ended_at, notes, is_active, created_by, created_at
                )
                VALUES (
                    :id_work_item, 'CONTRACT', :now, NULL, :notes, 1, :created_by, :now
                )
            """),
            {
                "id_work_item": id_work_item,
                "notes": "Stage berubah menjadi CONTRACT setelah kontrak dibuat.",
                "created_by": created_by,
                "now": now
            }
        )

    return {
        "id_contract": id_contract
    }


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


def delete_contract(id_contract, id_work_item, updated_by):
    now = get_wita()

    with engine.begin() as conn:

        # 1. Soft delete contract
        delete_query = text("""
            UPDATE work_contracts
            SET
                is_active = 0,
                updated_by = :updated_by,
                updated_at = :updated_at
            WHERE
                id_contract = :id_contract
                AND is_active = 1
        """)

        result = conn.execute(
            delete_query,
            {
                "id_contract": id_contract,
                "updated_by": updated_by,
                "updated_at": now
            }
        )

        if result.rowcount == 0:
            raise NotFoundError("Kontrak tidak ditemukan atau sudah tidak aktif.")

        # 2. Tentukan stage tujuan setelah contract dihapus
        stage_query = text("""
            SELECT
                CASE
                    WHEN EXISTS (
                        SELECT 1
                        FROM work_proposals
                        WHERE id_work_item = :id_work_item
                          AND is_active = 1
                    )
                    THEN 'QUOTATION'
                    ELSE 'IDENTIFIED'
                END AS previous_stage
        """)

        stage_result = conn.execute(
            stage_query,
            {
                "id_work_item": id_work_item
            }
        ).mappings().first()

        previous_stage = stage_result["previous_stage"]

        # 3. Tutup history CONTRACT yang sedang aktif
        close_history_query = text("""
            UPDATE work_stage_histories
            SET
                ended_at = :ended_at
            WHERE
                id_work_item = :id_work_item
                AND stage = 'CONTRACT'
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

        # 4. Rollback current stage Work Item
        update_work_query = text("""
            UPDATE work_items
            SET
                current_stage = :current_stage,
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
                "current_stage": previous_stage,
                "updated_by": updated_by,
                "updated_at": now
            }
        )

        # 5. Buat history stage baru
        insert_history_query = text("""
            INSERT INTO work_stage_histories (
                id_work_item, stage, started_at, ended_at, notes, is_active, created_by, created_at
            )
            VALUES (
                :id_work_item, :stage, :started_at, NULL, :notes, 1, :created_by, :created_at
            )
        """)

        conn.execute(
            insert_history_query,
            {
                "id_work_item": id_work_item,
                "stage": previous_stage,
                "started_at": now,
                "notes": "Rollback setelah kontrak dihapus.",
                "created_by": updated_by,
                "created_at": now
            }
        )

    return {
        "id_contract": id_contract,
        "id_work_item": id_work_item,
        "current_stage": previous_stage
    }