from datetime import datetime, timedelta
import calendar

from api.cashbook.constants import TRANSFER_CATEGORY_ID
from api.shared.exceptions import ValidationError
from api.utils.config import engine
from .query import *


# ============================================================================ #
#                     #SECTION - BASIC OPERATION TRANSACTION                   #
# ============================================================================ #

# ========================= #ANCHOR - LIST TRANSACTION ======================= #
def get_transaction_list_service(filters: dict):

    today = datetime.today().date()
    period = (filters.get("period") or "today").lower()

    if period not in ["today", "yesterday", "week", "month", "custom"]:
        raise ValidationError(
            "Period harus bernilai today, yesterday, week, month atau custom."
        )

    if period == "today":
        date_from = today
        date_to = today
        
    elif period == "yesterday":
        yesterday = today - timedelta(days=1)
        date_from = yesterday
        date_to = yesterday

    elif period == "week":
        monday = today - timedelta(days=today.weekday())
        sunday = monday + timedelta(days=6)
        date_from = monday
        date_to = sunday

    elif period == "month":
        date_from = today.replace(day=1)
        date_to = today.replace(
            day=calendar.monthrange(
                today.year,
                today.month
            )[1]
        )

    else:
        date_from = filters.get("date_from")
        date_to = filters.get("date_to")

        if not date_from or not date_to:
            raise ValidationError(
                "date_from dan date_to wajib diisi jika period = custom."
            )

    query_filters = {
        "id_account": filters.get("id_account"),
        "id_category": filters.get("id_category"),
        "transaction_type": filters.get("transaction_type"),
        "search": filters.get("search"),
        "created_by": filters.get("created_by"),
        "date_from": date_from,
        "date_to": date_to
    }

    accounts = get_transaction_accounts(query_filters)
    transactions = get_transaction_list(query_filters)
    opening_balances = get_opening_balances(date_from)
    summary = get_transaction_summary(query_filters)

    opening_balance_map = {row["id_account"]: row for row in opening_balances}

    transaction_map = {}

    for trx in transactions:
        id_account = trx["id_account"]

        if id_account not in transaction_map:
            transaction_map[id_account] = []

        transaction_map[id_account].append(dict(trx))

    result = []

    for account in accounts:
        id_account = account["id_account"]
        opening = opening_balance_map.get(id_account, {})
        opening_balance = opening.get("opening_balance", 0)
        starting_balance = opening.get("starting_balance", opening_balance)
        balance = starting_balance
        balance = starting_balance
        total_income = 0
        total_expense = 0
        account_transactions = []

        for trx in transaction_map.get(id_account, []):

            if trx["transaction_type"] == "IN":
                balance += trx["amount"]
                total_income += trx["amount"]
            else:
                balance -= trx["amount"]
                total_expense += trx["amount"]

            trx["balance_after"] = balance

            account_transactions.append(trx)

        result.append({
            "account": account,
            "opening_balance": opening_balance,
            "starting_balance": starting_balance,
            "ending_balance": balance,
            "total_income": total_income,
            "total_expense": total_expense,
            "transaction_count": len(account_transactions),
            "transactions": account_transactions
        })

    return {
        "summary": summary,
        "accounts": result
    }


# ======================== #ANCHOR - DETAIL TRANSACTION ====================== #
def get_transaction_detail_service(id_transaction: int):

    detail = get_transaction_detail(id_transaction)

    return {
        "id_transaction": detail["id_transaction"],

        "account": {
            "id_account": detail["id_account"],
            "account_name": detail["account_name"],
            "account_kind": detail["account_kind"],
            "bank_name": detail["bank_name"]
        },

        "category": {
            "id_category": detail["id_category"],
            "category_name": detail["category_name"]
        },

        "transaction_date": detail["transaction_date"],
        "transaction_type": detail["transaction_type"],
        "amount": detail["amount"],
        "transaction_description": detail["transaction_description"],
        "reference_number": detail["reference_number"],
        "attachment_url": detail["attachment_url"],

        "created_by": detail["created_by"],
        "created_at": detail["created_at"],
        "updated_by": detail["updated_by"],
        "updated_at": detail["updated_at"]
    }


# ======================== #ANCHOR - CREATE TRANSACTION ====================== #
def create_transaction_service(
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
    
    if amount <= 0:
        raise ValidationError("Amount harus lebih besar dari 0.")

    if transaction_type not in ["IN", "OUT"]:
        raise ValidationError("transaction_type harus IN atau OUT.")

    return create_transaction(
        id_account=id_account,
        id_category=id_category,
        transaction_date=transaction_date,
        transaction_type=transaction_type,
        amount=amount,
        transaction_description=transaction_description,
        reference_number=reference_number,
        attachment_url=attachment_url,
        created_by=created_by
    )


# ======================== #ANCHOR - UPDATE TRANSACTION ====================== #
def update_transaction_service(
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

    return update_transaction(
        id_transaction=id_transaction,
        id_account=id_account,
        id_category=id_category,
        transaction_date=transaction_date,
        transaction_type=transaction_type,
        amount=amount,
        transaction_description=transaction_description,
        reference_number=reference_number,
        attachment_url=attachment_url,
        updated_by=updated_by
    )



# ======================== #ANCHOR - DELETE TRANSACTION ====================== #
def delete_transaction_service(
    id_transaction: int,
    deleted_by: str
):

    return delete_transaction(
        id_transaction=id_transaction,
        deleted_by=deleted_by
    )


# ===================== #ANCHOR - BULK CREATE TRANSACTION ==================== #
def bulk_create_transaction_service(
    payload: list, 
    created_by: str
):
    if not payload:
        raise ValidationError("Transaction list cannot be empty.")
    
    transactions = []
    
    for item in payload:

        transactions.append({
            "id_account": item["id_account"],
            "id_category": item["id_category"],
            "transaction_date": item["transaction_date"],
            "transaction_type": item["transaction_type"],
            "amount": item["amount"],
            "transaction_description": item["transaction_description"],
            "reference_number": item.get("reference_number"),
            "attachment_url": item.get("attachment_url"),
            "created_by": created_by
        })

    return bulk_create_transaction(transactions)
# ================== #!SECTION - BASIC OPERATION TRANSACTION ================= #


# ============================================================================ #
#                          #SECTION - ACCOUNT TRANSFER                         #
# ============================================================================ #

# ========================= #ANCHOR - ACCOUNT TRANSFER ======================= #
def account_transfer_service(
    body: dict,
    created_by: str
):

    transactions = []

    with engine.begin() as conn:

        from_account = get_account_by_id(
            conn,
            body["id_from_account"]
        )

        if not from_account:
            raise ValidationError(
                "Account asal tidak ditemukan."
            )

        to_account = get_account_by_id(
            conn,
            body["id_to_account"]
        )

        if not to_account:
            raise ValidationError(
                "Account tujuan tidak ditemukan."
            )

        # Transfer Keluar
        # ---------------------------------------------------------------------------- #
        transactions.append({
            "id_account": body["id_from_account"],
            "id_category": TRANSFER_CATEGORY_ID,
            "transaction_date": body["transaction_date"],
            "transaction_type": "OUT",
            "amount": body["amount"],
            "transaction_description": body["description"],
            "reference_number": body.get("reference_number"),
            "attachment_url": body.get("attachment_url"),
            "created_by": created_by
        })

        # Transfer Masuk
        # ---------------------------------------------------------------------------- #
        transactions.append({
            "id_account": body["id_to_account"],
            "id_category": TRANSFER_CATEGORY_ID,
            "transaction_date": body["transaction_date"],
            "transaction_type": "IN",
            "amount": body["amount"],
            "transaction_description": body["description"],
            "reference_number": body.get("reference_number"),
            "attachment_url": body.get("attachment_url"),
            "created_by": created_by
        })

        # Optional Fees
        # ---------------------------------------------------------------------------- #
        for fee in body.get("fees", []):

            if fee["amount"] <= 0:
                continue

            transactions.append({
                "id_account": body["id_from_account"],
                "id_category": fee["id_category"],
                "transaction_date": body["transaction_date"],
                "transaction_type": "OUT",
                "amount": fee["amount"],
                "transaction_description": fee["description"],
                "reference_number": body.get("reference_number"),
                "attachment_url": body.get("attachment_url"),
                "created_by": created_by
            })

        bulk_create_transactions(
            conn,
            transactions
        )

    return {
        "transaction_created": len(transactions)
    }
# ======================== #!SECTION - ACCOUNT TRANSFER ====================== #