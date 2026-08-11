# api/cashbook/opening_balance/query.py
from sqlalchemy import text

from api.utils.config import engine
from api.shared.helper import get_wita


# ============================================================================ #
#                   #SECTION - BASIC OPERATION OPENING BALANCE                 #
# ============================================================================ #

# ======================= #ANCHOR - LIST OPENING BALANCE ===================== #

def get_opening_balance_list(filters: dict):
    sql = """
        SELECT
            ob.id_opening_balance,
            ob.id_account,
            a.account_name,
            ob.effective_date,
            ob.opening_balance,
            ob.notes,
            ob.created_by,
            ob.updated_by,
            ob.created_at,
            ob.updated_at
        FROM opening_balances ob
        JOIN accounts a
            ON a.id_account = ob.id_account
        WHERE
            ob.is_active = 1
    """

    params = {}

    if filters.get("id_account"):
        sql += """AND ob.id_account = :id_account"""

        params["id_account"] = int(filters["id_account"])

    if filters.get("effective_date"):
        sql += """AND ob.effective_date = :effective_date"""

        params["effective_date"] = filters["effective_date"]

    sql += """
        ORDER BY
            ob.effective_date DESC,
            a.account_name ASC
    """

    with engine.connect() as conn:
        return conn.execute(text(sql), params).mappings().all()


# ======================= #ANCHOR - GET OPENING BALANCE ====================== #

def get_opening_balance(id_account: int, effective_date: str):
    sql = text("""
        SELECT
            id_opening_balance
        FROM opening_balances
        WHERE
            id_account = :id_account
            AND effective_date = :effective_date
            AND is_active = 1
        LIMIT 1
    """)

    with engine.connect() as conn:
        return conn.execute(sql, {"id_account": id_account, "effective_date": effective_date}).mappings().first()


# ======================= #ANCHOR - LAST OPENING BALANCE ===================== #

def get_last_opening_balance(id_account: int):
    sql = text("""
        SELECT
            id_opening_balance,
            effective_date
        FROM opening_balances
        WHERE
            id_account = :id_account
            AND is_active = 1
        ORDER BY
            effective_date DESC
        LIMIT 1
    """)

    with engine.connect() as conn:
        return conn.execute(sql, {"id_account": id_account}).mappings().first()


# ======================= #ANCHOR - CREATE OPENING BALANCE =================== #

def create_opening_balance(
    body: dict
):

    sql = text("""
        INSERT INTO opening_balances
            (id_account, effective_date, opening_balance, notes, created_by, created_at, updated_at)
        VALUES
            (:id_account, :effective_date, :opening_balance, :notes, :created_by, :now, :now)
        RETURNING id_opening_balance
    """)

    with engine.begin() as conn:
        result = conn.execute(
            sql,
            {
                "id_account": body["id_account"],
                "effective_date": body["effective_date"],
                "opening_balance": body["opening_balance"],
                "notes": body.get("notes"),
                "created_by": body["created_by"],
                "now" : get_wita()
            }
        )

        return result.scalar()

# ================ #!SECTION - BASIC OPERATION OPENING BALANCE =============== #



# ============================================================================ #
#                  #SECTION - UPDATE OPERATION OPENING BALANCE                 #
# ============================================================================ #

# ==================== #ANCHOR - DETAIL OPENING BALANCE ====================== #

def get_opening_balance_by_id(id_opening_balance: int):
    sql = text("""
        SELECT
            id_opening_balance,
            id_account,
            effective_date
        FROM opening_balances
        WHERE
            id_opening_balance = :id_opening_balance
            AND is_active = 1
    """)

    with engine.connect() as conn:
        return conn.execute(
            sql,
            {
                "id_opening_balance": id_opening_balance
            }
        ).mappings().first()


# =================== #ANCHOR - PREVIOUS OPENING BALANCE ===================== #

def get_previous_opening_balance(id_opening_balance: int, id_account: int):
    sql = text("""
        SELECT
            id_opening_balance,
            effective_date
        FROM opening_balances
        WHERE
            id_account = :id_account
            AND id_opening_balance != :id_opening_balance
            AND is_active = 1
        ORDER BY
            effective_date DESC
    """)

    with engine.connect() as conn:
        rows = conn.execute(
            sql,
            {
                "id_account": id_account,
                "id_opening_balance": id_opening_balance
            }
        ).mappings().all()

    current = get_opening_balance_by_id(id_opening_balance)

    if not current:
        return None

    for row in rows:
        if row["effective_date"] < current["effective_date"]:
            return row

    return None


# ====================== #ANCHOR - NEXT OPENING BALANCE ====================== #

def get_next_opening_balance(id_opening_balance: int, id_account: int):
    sql = text("""
        SELECT
            id_opening_balance,
            effective_date
        FROM opening_balances
        WHERE
            id_account = :id_account
            AND id_opening_balance != :id_opening_balance
            AND is_active = 1
        ORDER BY
            effective_date ASC
    """)

    with engine.connect() as conn:
        rows = conn.execute(
            sql,
            {
                "id_account": id_account,
                "id_opening_balance": id_opening_balance
            }
        ).mappings().all()

    current = get_opening_balance_by_id(id_opening_balance)

    if not current:
        return None

    for row in rows:
        if row["effective_date"] > current["effective_date"]:
            return row

    return None


# ===================== #ANCHOR - DETAIL OPENING BALANCE ===================== #

def get_opening_balance_detail(id_opening_balance: int):

    sql = """
        SELECT
            ob.id_opening_balance,
            ob.id_account,
            a.account_name,
            ob.effective_date,
            ob.opening_balance,
            ob.notes,
            ob.created_by,
            ob.updated_by,
            ob.created_at,
            ob.updated_at
        FROM opening_balances ob
        JOIN accounts a
            ON a.id_account = ob.id_account
        WHERE
            ob.id_opening_balance = :id_opening_balance
            AND ob.is_active = 1
    """

    with engine.connect() as conn:
        return conn.execute(
            text(sql),
            {"id_opening_balance": id_opening_balance}
        ).mappings().first()


# ======================= #ANCHOR - UPDATE OPENING BALANCE =================== #

def update_opening_balance(id_opening_balance: int, body: dict):
    sql = text("""
        UPDATE opening_balances
        SET
            id_account = :id_account,
            effective_date = :effective_date,
            opening_balance = :opening_balance,
            notes = :notes,
            updated_by = :updated_by,
            updated_at = :now
        WHERE
            id_opening_balance = :id_opening_balance
            AND is_active = 1
    """)

    with engine.begin() as conn:
        conn.execute(
            sql,
            {
                "id_opening_balance": id_opening_balance,
                "id_account": body["id_account"],
                "effective_date": body["effective_date"],
                "opening_balance": body["opening_balance"],
                "notes": body.get("notes"),
                "updated_by": body["updated_by"],
                "now" : get_wita()
            }
        )

# ================ #!SECTION - UPDATE OPERATION OPENING BALANCE ============== #



# ============================================================================ #
#                 #SECTION - GENERATE OPERATION OPENING BALANCE                #
# ============================================================================ #

# ====================== #ANCHOR - GET LATEST CHECKPOINT ===================== #

def get_latest_checkpoint():

    sql = text("""
        SELECT
            effective_date
        FROM opening_balances
        WHERE
            is_active = 1
        ORDER BY
            effective_date DESC
        LIMIT 1
    """)

    with engine.connect() as conn:

        return conn.execute(
            sql
        ).mappings().first()


# ======================= #ANCHOR - GET ACTIVE ACCOUNT ======================= #

def get_active_accounts():

    sql = text("""
        SELECT
            id_account,
            account_name
        FROM accounts
        WHERE
            is_active = 1
        ORDER BY
            account_name
    """)

    with engine.connect() as conn:

        return conn.execute(
            sql
        ).mappings().all()


# ===================== #ANCHOR - GET OPENING SNAPSHOT ======================= #

def get_opening_snapshot(
    conn,
    effective_date: str
):

    sql = text("""
        SELECT
            ob.id_account,
            ob.opening_balance
        FROM opening_balances ob
        INNER JOIN (
            SELECT
                id_account,
                MAX(effective_date) AS effective_date
            FROM opening_balances
            WHERE
                effective_date < :effective_date
                AND is_active = 1
            GROUP BY
                id_account
        ) latest
            ON latest.id_account = ob.id_account
            AND latest.effective_date = ob.effective_date
    """)

    rows = conn.execute(
        sql,
        {
            "effective_date": effective_date
        }
    ).mappings().all()

    return {
        row["id_account"]: row["opening_balance"]
        for row in rows
    }


# ===================== #ANCHOR - GET ACCOUNT MOVEMENTS ====================== #

def get_account_movements(
    conn,
    effective_date: str
):

    sql = text("""
        SELECT
            a.id_account,
            COALESCE(
                SUM(
                    CASE
                        WHEN t.transaction_type = 'IN'
                            THEN t.amount
                        ELSE
                            -t.amount
                    END
                ),
                0
            ) AS movement
        FROM accounts a
        LEFT JOIN (
            SELECT
                id_account,
                MAX(effective_date) AS effective_date
            FROM opening_balances
            WHERE
                effective_date < :effective_date
                AND is_active = 1
            GROUP BY
                id_account
        ) ob
            ON ob.id_account = a.id_account
        LEFT JOIN transactions t
            ON t.id_account = a.id_account
            AND t.is_active = 1
            AND t.transaction_date >= COALESCE(
                ob.effective_date,
                DATE '1900-01-01'
            )
            AND t.transaction_date < :effective_date
        WHERE
            a.is_active = 1
        GROUP BY
            a.id_account
        ORDER BY
            a.id_account
    """)

    rows = conn.execute(
        sql,
        {
            "effective_date": effective_date
        }
    ).mappings().all()

    return {
        row["id_account"]: row["movement"]
        for row in rows
    }


# ==================== #ANCHOR - BULK CREATE OPENING BALANCE ================= #

def bulk_create_opening_balance(conn, opening_balances: list):

    sql = text("""
        INSERT INTO opening_balances
            (id_account, effective_date, opening_balance, notes, created_by, created_at, updated_at)
        VALUES
            (:id_account, :effective_date, :opening_balance, :notes, :created_by, :created_at, :updated_at)
    """)

    conn.execute(sql, opening_balances)

    return len(opening_balances)

# =============== #!SECTION - GENERATE OPERATION OPENING BALANCE ============= #


# ===================== #ANCHOR - DISPLAY OPENING BALANCE ==================== #

def get_opening_balance_display():
    sql = """
        SELECT
            ob.id_opening_balance,
            ob.id_account,
            a.account_name,
            a.account_kind,
            ob.effective_date,
            ob.opening_balance,
            ob.notes,
            ob.created_by,
            ob.updated_by,
            ob.created_at,
            ob.updated_at
        FROM opening_balances ob
        JOIN accounts a
            ON a.id_account = ob.id_account
        JOIN (
            SELECT
                id_account,
                MAX(effective_date) AS effective_date
            FROM opening_balances
            WHERE is_active = 1
            GROUP BY id_account
        ) latest
            ON latest.id_account = ob.id_account
           AND latest.effective_date = ob.effective_date
        WHERE
            ob.is_active = 1
        ORDER BY
            a.account_name ASC
    """

    with engine.connect() as conn:
        return conn.execute(text(sql)).mappings().all()