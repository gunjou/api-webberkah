# api/cashbook/account/query.py
from sqlalchemy import text

from api.utils.config import engine
from api.shared.helper import get_wita


# ============================================================================ #
#                      #SECTION - BASIC OPERATION ACCOUNT                      #
# ============================================================================ #

# =========================== #ANCHOR - LIST ACCOUNT ========================= #
def get_account_list():

    sql = text("""
        SELECT
            id_account,
            account_name,
            account_kind,
            bank_name,
            account_type,
            branch_name,
            account_number,
            account_holder,
            created_at,
            updated_at
        FROM accounts
        WHERE is_active = 1
        ORDER BY
            account_name ASC
    """)

    with engine.connect() as conn:
        return conn.execute(sql).mappings().all()


# ========================== #ANCHOR - DETAIL ACCOUNT ======================== #
def get_account_detail(
    id_account: int
):

    sql = text("""
        SELECT
            id_account,
            account_name,
            account_kind,
            bank_name,
            account_type,
            branch_name,
            account_number,
            account_holder,
            created_by,
            updated_by,
            deleted_by,
            created_at,
            updated_at,
            deleted_at
        FROM accounts
        WHERE
            id_account = :id_account
            AND is_active = 1
    """)

    with engine.connect() as conn:
        return conn.execute(
            sql,
            {
                "id_account": id_account
            }
        ).mappings().first()


# ========================== #ANCHOR - CREATE ACCOUNT ======================== #
def create_account(
    account_name: str,
    account_kind: str,
    bank_name: str,
    account_type: str,
    branch_name: str,
    account_number: str,
    account_holder: str,
    created_by: str
):

    sql = text("""
        INSERT INTO accounts
        (
            account_name,
            account_kind,
            bank_name,
            account_type,
            branch_name,
            account_number,
            account_holder,
            created_at,
            updated_at,
            created_by
        )
        VALUES
        (
            :account_name,
            :account_kind,
            :bank_name,
            :account_type,
            :branch_name,
            :account_number,
            :account_holder,
            :now,
            :now,
            :created_by
        )
        RETURNING id_account
    """)

    with engine.begin() as conn:

        result = conn.execute(
            sql,
            {
                "account_name": account_name,
                "account_kind": account_kind,
                "bank_name": bank_name,
                "account_type": account_type,
                "branch_name": branch_name,
                "account_number": account_number,
                "account_holder": account_holder,
                "now": get_wita(),
                "created_by": created_by
            }
        )

        return result.scalar()


# ========================== #ANCHOR - UPDATE ACCOUNT ======================== #
def update_account(
    id_account: int,
    account_name: str,
    account_kind: str,
    bank_name: str,
    account_type: str,
    branch_name: str,
    account_number: str,
    account_holder: str,
    updated_by: str
):

    sql = text("""
        UPDATE accounts
        SET
            account_name = :account_name,
            account_kind = :account_kind,
            bank_name = :bank_name,
            account_type = :account_type,
            branch_name = :branch_name,
            account_number = :account_number,
            account_holder = :account_holder,
            updated_by = :updated_by,
            updated_at = :now
        WHERE
            id_account = :id_account
            AND is_active = 1
        RETURNING id_account
    """)

    with engine.begin() as conn:

        result = conn.execute(
            sql,
            {
                "id_account": id_account,
                "account_name": account_name,
                "account_kind": account_kind,
                "bank_name": bank_name,
                "account_type": account_type,
                "branch_name": branch_name,
                "account_number": account_number,
                "account_holder": account_holder,
                "updated_by": updated_by,
                "now": get_wita()
            }
        )

        return result.rowcount


# ========================== #ANCHOR - DELETE ACCOUNT ======================== #
def delete_account(
    id_account: int,
    deleted_by: str
):

    sql = text("""
        UPDATE accounts
        SET
            is_active = 0,
            deleted_by = :deleted_by,
            deleted_at = :now
        WHERE
            id_account = :id_account
            AND is_active = 1
    """)

    with engine.begin() as conn:

        result = conn.execute(
            sql,
            {
                "id_account": id_account,
                "deleted_by": deleted_by,
                "now": get_wita()
            }
        )

        return result.rowcount


# ======================== #ANCHOR - DROPDOWN ACCOUNT ======================== #
def get_account_dropdown():
    sql = text("""SELECT id_account, account_name FROM accounts WHERE is_active = 1 ORDER BY account_name ASC""")
    with engine.connect() as conn: 
        return conn.execute(sql).mappings().all()
    
# ==================== #!SECTION - BASIC OPERATION ACCOUNT =================== #