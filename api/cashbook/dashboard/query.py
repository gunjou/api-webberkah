# api/cashbook/dashboard/query.py
from sqlalchemy import text
from api.utils.config import engine


def get_dashboard_summary(filters: dict):

    sql = """
        SELECT
            COALESCE(SUM(CASE WHEN t.transaction_type='IN' THEN t.amount ELSE 0 END),0) total_income,
            COALESCE(SUM(CASE WHEN t.transaction_type='OUT' THEN t.amount ELSE 0 END),0) total_expense,
            COALESCE(SUM(CASE WHEN t.transaction_type='IN' THEN t.amount ELSE -t.amount END),0) net_cashflow
        FROM transactions t
        INNER JOIN categories c ON c.id_category=t.id_category AND c.is_reportable=1
        WHERE t.is_active=1
          AND t.transaction_date BETWEEN :date_from AND :date_to
    """

    params = {
        "date_from": filters["date_from"],
        "date_to": filters["date_to"]
    }

    if filters.get("id_account"):
        sql += " AND t.id_account=:id_account"
        params["id_account"] = filters["id_account"]

    with engine.connect() as conn:
        return conn.execute(text(sql), params).mappings().first()


def get_current_balance(id_account=None):
    sql = """
        WITH latest_opening AS (
            SELECT DISTINCT ON (ob.id_account)
                ob.id_account,
                ob.opening_balance,
                ob.effective_date
            FROM opening_balances ob
            WHERE ob.is_active = 1
    """

    params = {}

    if id_account:
        sql += " AND ob.id_account = :id_account"
        params["id_account"] = id_account

    sql += """
            ORDER BY ob.id_account, ob.effective_date DESC
        )
        SELECT
            COALESCE(
                SUM(lo.opening_balance + COALESCE(trx.balance, 0)),
                0
            ) AS current_balance
        FROM latest_opening lo
        LEFT JOIN (
            SELECT
                t.id_account,
                SUM(
                    CASE
                        WHEN t.transaction_type = 'IN' THEN t.amount
                        ELSE -t.amount
                    END
                ) AS balance
            FROM transactions t
            WHERE t.is_active = 1
    """

    if id_account:
        sql += " AND t.id_account = :id_account"

    sql += """
            GROUP BY t.id_account
        ) trx ON trx.id_account = lo.id_account
    """

    with engine.connect() as conn:
        row = conn.execute(text(sql), params).mappings().first()

    return row["current_balance"] or 0


def get_dashboard_cashflow(filters: dict):
    period = filters["period"]

    if period == "week":
        group_sql = "EXTRACT(ISODOW FROM t.transaction_date)"
    elif period == "month":
        group_sql = "EXTRACT(DAY FROM t.transaction_date)"
    else:
        group_sql = "EXTRACT(MONTH FROM t.transaction_date)"

    sql = f"""
        SELECT
            {group_sql}::INTEGER AS label,
            COALESCE(
                SUM(CASE
                    WHEN t.transaction_type = 'IN' THEN t.amount
                    ELSE 0
                END), 0
            ) AS income,
            COALESCE(
                SUM(CASE
                    WHEN t.transaction_type = 'OUT' THEN t.amount
                    ELSE 0
                END), 0
            ) AS expense
        FROM transactions t
        INNER JOIN categories c
            ON c.id_category = t.id_category
            AND c.is_reportable = 1
        WHERE t.is_active = 1
            AND t.transaction_date BETWEEN :date_from AND :date_to
    """

    params = {
        "date_from": filters["date_from"],
        "date_to": filters["date_to"],
    }

    if filters.get("id_account"):
        sql += " AND t.id_account = :id_account"
        params["id_account"] = filters["id_account"]

    sql += f"""
        GROUP BY {group_sql}
        ORDER BY {group_sql}
    """

    with engine.connect() as conn:
        return conn.execute(text(sql), params).mappings().all()


def get_dashboard_recent_transactions(filters: dict):
    sql = """
        SELECT
            t.id_transaction,
            t.transaction_type,
            t.transaction_description,
            c.name AS category_name,
            a.account_name,
            t.amount,
            t.transaction_date,
            TO_CHAR(t.created_at, 'YYYY-MM-DD HH24:MI') AS created_at
        FROM transactions t
        INNER JOIN categories c
            ON c.id_category = t.id_category
            AND c.is_reportable = 1
        INNER JOIN accounts a
            ON a.id_account = t.id_account
        WHERE t.is_active = 1
            AND t.transaction_date BETWEEN :date_from AND :date_to
    """

    params = {
        "date_from": filters["date_from"],
        "date_to": filters["date_to"],
    }

    if filters.get("id_account"):
        sql += " AND t.id_account = :id_account"
        params["id_account"] = filters["id_account"]

    sql += """
        ORDER BY t.transaction_date DESC, t.id_transaction DESC
        LIMIT 5
    """

    with engine.connect() as conn:
        return conn.execute(text(sql), params).mappings().all()


def get_dashboard_expense_category(filters: dict):
    sql = """
        SELECT
            c.id_category,
            c.name AS category_name,
            SUM(t.amount) AS amount,
            ROUND(
                (
                    SUM(t.amount) / NULLIF(SUM(SUM(t.amount)) OVER (), 0)
                ) * 100
            )::INTEGER AS percentage
        FROM transactions t
        INNER JOIN categories c
            ON c.id_category = t.id_category
            AND c.is_reportable = 1
        WHERE t.is_active = 1
            AND t.transaction_type = 'OUT'
            AND t.transaction_date BETWEEN :date_from AND :date_to
    """

    params = {
        "date_from": filters["date_from"],
        "date_to": filters["date_to"],
    }

    if filters.get("id_account"):
        sql += " AND t.id_account = :id_account"
        params["id_account"] = filters["id_account"]

    sql += """
        GROUP BY c.id_category, c.name
        ORDER BY amount DESC
        LIMIT 5
    """

    with engine.connect() as conn:
        return conn.execute(text(sql), params).mappings().all()


def get_dashboard_expense_account(filters: dict):
    sql = """
        SELECT
            a.id_account,
            a.account_name,
            SUM(t.amount) AS amount,
            ROUND(
                (
                    SUM(t.amount) /
                    NULLIF(SUM(SUM(t.amount)) OVER (), 0)
                ) * 100
            )::INTEGER AS percentage
        FROM transactions t
        INNER JOIN accounts a
            ON a.id_account = t.id_account
        INNER JOIN categories c
            ON c.id_category = t.id_category
            AND c.is_reportable = 1
        WHERE t.is_active = 1
            AND t.transaction_type = 'OUT'
            AND t.transaction_date BETWEEN :date_from AND :date_to
    """

    params = {
        "date_from": filters["date_from"],
        "date_to": filters["date_to"],
    }

    # if filters.get("id_account"):
    #     sql += " AND t.id_account = :id_account"
    #     params["id_account"] = filters["id_account"]

    sql += """
        GROUP BY a.id_account, a.account_name
        ORDER BY amount DESC
    """

    with engine.connect() as conn:
        return conn.execute(text(sql), params).mappings().all()