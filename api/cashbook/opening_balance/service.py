# api/cashbook/opening_balance/service.py
from datetime import datetime

from api.shared.exceptions import ValidationError, NotFoundError
from .query import *


# ============================================================================ #
#                   #SECTION - BASIC OPERATION OPENING BALANCE                 #
# ============================================================================ #

# ======================= #ANCHOR - LIST OPENING BALANCE ===================== #
def get_opening_balance_list_service(filters: dict):
    return get_opening_balance_list(filters)


# ======================= #ANCHOR - CREATE OPENING BALANCE =================== #

def create_opening_balance_service(body: dict):
    
    opening_balance = get_opening_balance(id_account=body["id_account"], effective_date=body["effective_date"])

    if opening_balance:
        raise ValidationError("Opening balance pada tanggal tersebut sudah ada.")

    last_opening = get_last_opening_balance(body["id_account"])
    
    effective_date = datetime.strptime(body["effective_date"], "%Y-%m-%d").date()

    if (last_opening and effective_date <= last_opening["effective_date"]):
        raise ValidationError("Tanggal effective harus lebih besar dari checkpoint terakhir.")

    return create_opening_balance(body)


# ================ #!SECTION - BASIC OPERATION OPENING BALANCE =============== #



# ============================================================================ #
#                  #SECTION - UPDATE OPERATION OPENING BALANCE                 #
# ============================================================================ #

# ==================== #ANCHOR - DETAIL OPENING BALANCE ====================== #

def get_opening_balance_detail_service(id_opening_balance: int):

    opening_balance = get_opening_balance_detail(id_opening_balance)

    if not opening_balance:
        raise NotFoundError("Opening balance tidak ditemukan.")

    return opening_balance


# ======================= #ANCHOR - UPDATE OPENING BALANCE =================== #

def update_opening_balance_service(id_opening_balance: int, body: dict):

    opening_balance = get_opening_balance_by_id(id_opening_balance)

    if not opening_balance:
        raise NotFoundError("Opening balance tidak ditemukan.")

    duplicate = get_opening_balance(
        id_account=body["id_account"],
        effective_date=body["effective_date"]
    )

    if (duplicate and duplicate["id_opening_balance"] != id_opening_balance):
        raise ValidationError("Opening balance pada tanggal tersebut sudah ada.")

    effective_date = datetime.strptime(body["effective_date"], "%Y-%m-%d").date()

    previous = get_previous_opening_balance(
        id_opening_balance=id_opening_balance,
        id_account=body["id_account"]
    )

    if (previous and effective_date <= previous["effective_date"]):
        raise ValidationError("Tanggal effective harus lebih besar dari checkpoint sebelumnya.")

    next_opening = get_next_opening_balance(
        id_opening_balance=id_opening_balance,
        id_account=body["id_account"]
    )

    if (next_opening and effective_date >= next_opening["effective_date"]):
        raise ValidationError("Tanggal effective harus lebih kecil dari checkpoint berikutnya.")

    update_opening_balance(
        id_opening_balance=id_opening_balance,
        body=body
    )

# ================ #!SECTION - UPDATE OPERATION OPENING BALANCE ============== #



# ============================================================================ #
#                 #SECTION - GENERATE OPERATION OPENING BALANCE                #
# ============================================================================ #

# ===================== #ANCHOR - GENERATE OPENING BALANCE =================== #

def generate_opening_balance_service(body: dict):

    effective_date = datetime.strptime(
        body["effective_date"],
        "%Y-%m-%d"
    ).date()

    latest_checkpoint = get_latest_checkpoint()

    if latest_checkpoint:

        if effective_date <= latest_checkpoint["effective_date"]:
            raise ValidationError(
                "Effective date harus lebih besar dari checkpoint terakhir."
            )

    accounts = get_active_accounts()

    if not accounts:
        raise ValidationError(
            "Tidak ada account aktif."
        )

    with engine.begin() as conn:

        opening_snapshot = get_opening_snapshot(
            conn=conn,
            effective_date=body["effective_date"]
        )

        account_movements = get_account_movements(
            conn=conn,
            effective_date=body["effective_date"]
        )

        opening_balances = []

        for account in accounts:

            id_account = account["id_account"]

            opening_balance = opening_snapshot.get(
                id_account,
                0
            )

            movement = account_movements.get(
                id_account,
                0
            )

            opening_balances.append({
                "id_account": id_account,
                "effective_date": body["effective_date"],
                "opening_balance": opening_balance + movement,
                "notes": body.get("notes"),
                "created_by": body["created_by"]
            })

        bulk_create_opening_balance(
            conn=conn,
            opening_balances=opening_balances
        )

    return {
        "generated_account": len(opening_balances),
        "effective_date": body["effective_date"]
    }

# =============== #!SECTION - GENERATE OPERATION OPENING BALANCE ============= #


# ==================== #ANCHOR - DISPLAY OPENING BALANCE ===================== #

def get_opening_balance_display_service():
    return get_opening_balance_display()