from sqlalchemy import text

from api.cashbook.constants import TRANSFER_CATEGORY_ID
from api.utils.config import engine
from api.shared.helper import get_wita


# ============================================================================ #
#                     #SECTION - BASIC OPERATION TRANSACTION                   #
# ============================================================================ #

# ======================= #ANCHOR - LIST ACCOUNT ============================= #

def get_transaction_accounts(filters: dict):

    sql = """SELECT id_account, account_name, account_kind, bank_name FROM accounts WHERE is_active = 1 """

    params = {}

    if filters.get("id_account"):
        sql += """ AND id_account = :id_account"""
        params["id_account"] = filters["id_account"]

    sql += """ ORDER BY account_name ASC"""

    with engine.connect() as conn:
        return conn.execute(text(sql), params).mappings().all()

# ==================== #ANCHOR - LIST TRANSACTION DATA ======================= #

def get_transaction_list(filters: dict):

    sql = """
        SELECT
            t.id_transaction,
            t.id_account,
            t.transaction_date,
            t.transaction_type,
            t.id_category,
            c.name AS category_name,
            t.transaction_description,
            t.reference_number,
            t.amount,
            t.attachment_url,
            t.created_by,
            t.created_at
        FROM transactions t
        INNER JOIN categories c
            ON c.id_category = t.id_category
           AND c.is_reportable = 1
        WHERE
            t.is_active = 1
    """

    params = {}

    if filters.get("date_from"):
        sql += """
            AND t.transaction_date >= :date_from
        """
        params["date_from"] = filters["date_from"]

    if filters.get("date_to"):
        sql += """
            AND t.transaction_date <= :date_to
        """
        params["date_to"] = filters["date_to"]

    if filters.get("id_account"):
        sql += """
            AND t.id_account = :id_account
        """
        params["id_account"] = filters["id_account"]

    if filters.get("id_category"):
        sql += """
            AND t.id_category = :id_category
        """
        params["id_category"] = filters["id_category"]

    if filters.get("transaction_type"):
        sql += """
            AND t.transaction_type = :transaction_type
        """
        params["transaction_type"] = filters["transaction_type"]

    if filters.get("created_by"):
        sql += """
            AND t.created_by = :created_by
        """
        params["created_by"] = filters["created_by"]

    if filters.get("search"):
        sql += """
            AND (
                LOWER(t.transaction_description) LIKE LOWER(:search)
                OR LOWER(t.reference_number) LIKE LOWER(:search)
                OR LOWER(c.name) LIKE LOWER(:search)
            )
        """
        params["search"] = f"%{filters['search']}%"

    sql += """
        ORDER BY
            t.id_account,
            t.transaction_date,
            t.id_transaction
    """

    with engine.connect() as conn:
        return conn.execute(text(sql), params).mappings().all()


# ===================== #ANCHOR - OPENING BALANCE ============================ #

def get_opening_balances(date_from):

    sql = """
        WITH latest_opening AS (

            SELECT
                ob.id_account,
                ob.opening_balance,
                ob.effective_date

            FROM opening_balances ob

            INNER JOIN (

                SELECT
                    id_account,
                    MAX(effective_date) AS effective_date

                FROM opening_balances

                WHERE
                    is_active = 1
                    AND effective_date <= :date_from

                GROUP BY
                    id_account

            ) latest
                ON latest.id_account = ob.id_account
               AND latest.effective_date = ob.effective_date
        )

        SELECT
            lo.id_account,
            lo.opening_balance,
            lo.effective_date,

            lo.opening_balance +
            COALESCE(

                SUM(

                    CASE

                        WHEN t.transaction_type = 'IN'
                        THEN t.amount

                        ELSE -t.amount

                    END

                ),

                0

            ) AS starting_balance

        FROM latest_opening lo

        LEFT JOIN transactions t
            ON t.id_account = lo.id_account
           AND t.is_active = 1
           AND t.transaction_date >= lo.effective_date
           AND t.transaction_date < :date_from

        GROUP BY
            lo.id_account,
            lo.opening_balance,
            lo.effective_date
    """

    with engine.connect() as conn:

        return conn.execute(
            text(sql),
            {
                "date_from": date_from
            }
        ).mappings().all()


# ====================== #ANCHOR - BALANCE ADJUSTMENT ======================== #

def get_balance_adjustments(opening_balances: list, date_from):

    if not opening_balances:
        return {}

    sql = """
        SELECT
            ob.id_account,

            COALESCE(
                SUM(
                    CASE
                        WHEN t.transaction_type = 'IN'
                        THEN t.amount
                        ELSE -t.amount
                    END
                ),
                0
            ) AS adjustment

        FROM (
    """

    params = {
        "date_from": date_from
    }

    union_sql = []

    for i, item in enumerate(opening_balances):

        union_sql.append(f"""
            SELECT
                :id_account_{i} AS id_account,
                :effective_date_{i} AS effective_date
        """)

        params[f"id_account_{i}"] = item["id_account"]
        params[f"effective_date_{i}"] = item["effective_date"]

    sql += " UNION ALL ".join(union_sql)

    sql += """
        ) ob

        LEFT JOIN transactions t
            ON t.id_account = ob.id_account
           AND t.is_active = 1
           AND t.transaction_date >= ob.effective_date
           AND t.transaction_date < :date_from

        GROUP BY
            ob.id_account
    """

    with engine.connect() as conn:

        rows = conn.execute(
            text(sql),
            params
        ).mappings().all()

    return {
        row["id_account"]: row["adjustment"]
        for row in rows
    }


# ====================== #ANCHOR - TRANSACTION SUMMARY =======================

def get_transaction_summary(filters: dict):

    sql = """
        SELECT

            -- Income tanpa transfer
            COALESCE(
                SUM(
                    CASE
                        WHEN t.transaction_type = 'IN'
                         AND t.id_category != :transfer_category_id
                        THEN t.amount
                        ELSE 0
                    END
                ),
                0
            ) AS total_income,

            -- Outcome tanpa transfer
            COALESCE(
                SUM(
                    CASE
                        WHEN t.transaction_type = 'OUT'
                         AND t.id_category != :transfer_category_id
                        THEN t.amount
                        ELSE 0
                    END
                ),
                0
            ) AS total_outcome,

            -- Cashflow tanpa transfer
            COALESCE(
                SUM(
                    CASE
                        WHEN t.id_category = :transfer_category_id
                        THEN 0

                        WHEN t.transaction_type = 'IN'
                        THEN t.amount

                        ELSE -t.amount
                    END
                ),
                0
            ) AS cashflow,

            -- Semua transaksi
            COUNT(*) AS total_transaction_count,

            -- Khusus transfer
            COUNT(*) FILTER (
                WHERE t.id_category = :transfer_category_id
            ) AS transfer_count,

            -- Transaksi selain transfer
            COUNT(*) FILTER (
                WHERE t.id_category != :transfer_category_id
            ) AS transaction_count

        FROM transactions t

        INNER JOIN categories c
            ON c.id_category = t.id_category
           AND c.is_reportable = 1

        WHERE
            t.is_active = 1
    """

    params = {
        "transfer_category_id": TRANSFER_CATEGORY_ID
    }

    if filters.get("date_from"):
        sql += """
            AND t.transaction_date >= :date_from
        """
        params["date_from"] = filters["date_from"]

    if filters.get("date_to"):
        sql += """
            AND t.transaction_date <= :date_to
        """
        params["date_to"] = filters["date_to"]

    if filters.get("id_account"):
        sql += """
            AND t.id_account = :id_account
        """
        params["id_account"] = filters["id_account"]

    if filters.get("id_category"):
        sql += """
            AND t.id_category = :id_category
        """
        params["id_category"] = filters["id_category"]

    if filters.get("transaction_type"):
        sql += """
            AND t.transaction_type = :transaction_type
        """
        params["transaction_type"] = filters["transaction_type"]

    if filters.get("created_by"):
        sql += """
            AND t.created_by = :created_by
        """
        params["created_by"] = filters["created_by"]

    if filters.get("search"):
        sql += """
            AND (
                LOWER(t.transaction_description) LIKE LOWER(:search)
                OR LOWER(t.reference_number) LIKE LOWER(:search)
                OR LOWER(c.name) LIKE LOWER(:search)
            )
        """
        params["search"] = f"%{filters['search']}%"

    with engine.connect() as conn:
        return conn.execute(
            text(sql),
            params
        ).mappings().first()


# ======================== #ANCHOR - DETAIL TRANSACTION ====================== #

def get_transaction_detail(id_transaction: int):

    sql = text("""
        SELECT
            t.id_transaction,

            a.id_account,
            a.account_name,
            a.account_kind,
            a.bank_name,

            c.id_category,
            c.name AS category_name,

            t.transaction_date,
            t.transaction_type,
            t.amount,
            t.transaction_description,
            t.reference_number,
            t.attachment_url,

            t.created_by,
            t.updated_by,
            t.created_at,
            t.updated_at

        FROM transactions t

        INNER JOIN accounts a
            ON a.id_account = t.id_account

        INNER JOIN categories c
            ON c.id_category = t.id_category

        WHERE
            t.id_transaction = :id_transaction
            AND t.is_active = 1
    """)

    with engine.connect() as conn:
        return conn.execute(
            sql,
            {
                "id_transaction": id_transaction
            }
        ).mappings().first()



# ======================== #ANCHOR - CREATE TRANSACTION ====================== #
def create_transaction(
    id_account: int,
    id_category: int,
    transaction_date: str,
    transaction_type: str,
    amount: float,
    transaction_description: str,
    reference_number: str,
    attachment_url: str,
    created_by: str
):

    sql = text("""
        INSERT INTO transactions
        (
            id_account,
            id_category,
            transaction_date,
            transaction_type,
            amount,
            transaction_description,
            reference_number,
            attachment_url,
            created_by,
            created_at,
            updated_at
        )
        VALUES
        (
            :id_account,
            :id_category,
            :transaction_date,
            :transaction_type,
            :amount,
            :transaction_description,
            :reference_number,
            :attachment_url,
            :created_by,
            :now,
            :now
        )
        RETURNING
            id_transaction,
            id_account,
            id_category,
            transaction_date,
            transaction_type,
            amount,
            transaction_description,
            reference_number,
            attachment_url,
            created_by,
            created_at,
            updated_at
    """)

    with engine.begin() as conn:

        return conn.execute(
            sql,
            {
                "id_account": id_account,
                "id_category": id_category,
                "transaction_date": transaction_date,
                "transaction_type": transaction_type,
                "amount": amount,
                "transaction_description": transaction_description,
                "reference_number": reference_number,
                "attachment_url": attachment_url,
                "created_by": created_by,
                "now": get_wita()
            }
        ).mappings().first()



# ======================== #ANCHOR - UPDATE TRANSACTION ====================== #
def update_transaction(
    id_transaction: int,
    id_account: int,
    id_category: int,
    transaction_date: str,
    transaction_type: str,
    amount: float,
    transaction_description: str,
    reference_number: str,
    attachment_url: str,
    updated_by: str
):

    sql = text("""
        UPDATE transactions
        SET
            id_account = :id_account,
            id_category = :id_category,
            transaction_date = :transaction_date,
            transaction_type = :transaction_type,
            amount = :amount,
            transaction_description = :transaction_description,
            reference_number = :reference_number,
            attachment_url = :attachment_url,
            updated_by = :updated_by,
            updated_at = :now
        WHERE
            id_transaction = :id_transaction
            AND is_active = 1
        RETURNING
            id_transaction,
            id_account,
            id_category,
            transaction_date,
            transaction_type,
            amount,
            transaction_description,
            reference_number,
            attachment_url,
            updated_by,
            updated_at
    """)

    with engine.begin() as conn:

        return conn.execute(
            sql,
            {
                "id_transaction": id_transaction,
                "id_account": id_account,
                "id_category": id_category,
                "transaction_date": transaction_date,
                "transaction_type": transaction_type,
                "amount": amount,
                "transaction_description": transaction_description,
                "reference_number": reference_number,
                "attachment_url": attachment_url,
                "updated_by": updated_by,
                "now": get_wita()
            }
        ).mappings().first()



# ======================== #ANCHOR - DELETE TRANSACTION ====================== #
def delete_transaction(
    id_transaction: int,
    deleted_by: str
):

    sql = text("""
        UPDATE transactions
        SET
            is_active = 0,
            deleted_by = :deleted_by,
            deleted_at = :now
        WHERE
            id_transaction = :id_transaction
            AND is_active = 1
        RETURNING
            id_transaction,
            deleted_by,
            deleted_at
    """)

    with engine.begin() as conn:

        return conn.execute(
            sql,
            {
                "id_transaction": id_transaction,
                "deleted_by": deleted_by,
                "now": get_wita()
            }
        ).mappings().first()



# ===================== #ANCHOR - BULK CREATE TRANSACTION ==================== #
def bulk_create_transaction(
    transactions: list
):

    sql = text("""
        INSERT INTO transactions
        (
            id_account,
            id_category,
            transaction_date,
            transaction_type,
            amount,
            transaction_description,
            reference_number,
            attachment_url,
            created_by,
            created_at,
            updated_at
        )
        VALUES
        (
            :id_account,
            :id_category,
            :transaction_date,
            :transaction_type,
            :amount,
            :transaction_description,
            :reference_number,
            :attachment_url,
            :created_by,
            :created_at,
            :updated_at
        )
    """)

    with engine.begin() as conn:

        conn.execute(
            sql,
            transactions
        )

    return {
        "total_inserted": len(transactions)
    }
# ================== #!SECTION - BASIC OPERATION TRANSACTION ================= #



# ============================================================================ #
#                         #SECTION - QUERY FOR TRANSFER                        #
# ============================================================================ #

# =========================== #ANCHOR - GET ACCOUNT ========================== #
def get_account_by_id(
    conn,
    id_account: int
):

    sql = text("""
        SELECT
            id_account,
            account_name
        FROM accounts
        WHERE
            id_account = :id_account
            AND is_active = 1
    """)

    return conn.execute(
        sql,
        {
            "id_account": id_account
        }
    ).mappings().first()


# ===================== #ANCHOR - BULK CREATE TRANSACTION ==================== #
def bulk_create_transactions(
    conn,
    transactions: list
):

    sql = text("""
        INSERT INTO transactions
        (
            id_account,
            id_category,
            transaction_date,
            transaction_type,
            amount,
            transaction_description,
            reference_number,
            attachment_url,
            created_by,
            created_at,
            updated_by
        )
        VALUES
        (
            :id_account,
            :id_category,
            :transaction_date,
            :transaction_type,
            :amount,
            :transaction_description,
            :reference_number,
            :attachment_url,
            :created_by,
            :created_at,
            :updated_at
        )
    """)

    conn.execute(
        sql,
        transactions
    )
# ======================= #!SECTION - QUERY FOR TRANSFER ====================== #