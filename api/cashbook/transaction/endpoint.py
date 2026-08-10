from flask import request
from flask_jwt_extended import jwt_required, get_jwt
from flask_restx import Resource, fields

from api.shared.response import success
from api.shared.exceptions import ValidationError, NotFoundError
from api.utils.decorator import measure_execution_time
from api.security.cashbook import cashbook_role_required

from . import ns
from .service import *


# ============================================================================ #
#                            #ANCHOR - SWAGGER MODEL                           #
# ============================================================================ #

transaction_model = ns.model(
    "Transaction", {
        "id_account": fields.Integer(required=True, description="Account ID"),
        "id_category": fields.Integer(required=True, description="Category ID"),
        "transaction_date": fields.String(required=True, description="Transaction Date"),
        "transaction_type": fields.String(required=True, enum=["IN", "OUT"]),
        "amount": fields.Float(required=True),
        "transaction_description": fields.String(required=True),
        "reference_number": fields.String(required=False),
        "attachment_url": fields.String(required=False, description="Attachment URL")
    }
)

bulk_transaction_model = ns.model(
    "BulkTransaction",
    {
        "id_account": fields.Integer(required=True),
        "id_category": fields.Integer(required=True),
        "transaction_date": fields.String(required=True),
        "transaction_type": fields.String(required=True, enum=["IN", "OUT"]),
        "amount": fields.Float(required=True),
        "transaction_description": fields.String(required=True),
        "reference_number": fields.String(required=False),
        "attachment_url": fields.String(required=False)
    }
)

# ACCOUNT TRANSFER MODEL
# ---------------------------------------------------------------------------- #
transfer_fee_model = ns.model(
    "TransferFee", {
        "id_category": fields.Integer(required=True, description="Fee Category"),
        "amount": fields.Float(required=True, description="Fee Amount"),
        "description": fields.String(required=True, description="Fee Description")
    }
)

account_transfer_model = ns.model(
    "AccountTransfer", {
        "id_from_account": fields.Integer(required=True, description="Source Account"),
        "id_to_account": fields.Integer(required=True, description="Destination Account"),
        "transfer_type": fields.String(required=True, enum=["TRANSFER", "WITHDRAW"]),
        "amount": fields.Float(required=True),
        "transaction_date": fields.String(required=True),
        "description": fields.String(required=True),
        "reference_number": fields.String(required=False),
        "fees": fields.List(fields.Nested(transfer_fee_model), required=False)
    }
)


# ============================================================================ #
#                            #ANCHOR - FILTER PARSER                           #
# ============================================================================ #

transaction_filter_parser = ns.parser()
transaction_filter_parser.add_argument("period", type=str, required=False, default="today", choices=["today", "yesterday", "week", "month", "custom"])
transaction_filter_parser.add_argument("id_account", type=int, required=False)
transaction_filter_parser.add_argument("id_category", type=int, required=False)
transaction_filter_parser.add_argument("transaction_type", type=str, required=False, choices=["IN", "OUT"])
transaction_filter_parser.add_argument("search", type=str, required=False)
transaction_filter_parser.add_argument("date_from", type=str, required=False)
transaction_filter_parser.add_argument("date_to", type=str, required=False)
transaction_filter_parser.add_argument("created_by", type=str, required=False)

# ============================================================================ #
#                     #SECTION - BASIC OPERATION TRANSACTION                   #
# ============================================================================ #

# ========================== #ANCHOR - LIST & CREATE ========================= #

@ns.route("")
class TransactionListResource(Resource):

    @jwt_required()
    @cashbook_role_required()
    @ns.expect(transaction_filter_parser)
    @measure_execution_time
    def get(self):
        """Cashbook Transaction"""

        filters = request.args.to_dict()
        data = get_transaction_list_service(filters)

        return success(data=data, message="List transaction")

    @jwt_required()
    @cashbook_role_required()
    @ns.expect(transaction_model)
    @measure_execution_time
    def post(self):
        """Create Transaction"""

        payload = request.get_json()
        jwt_data = get_jwt()
        created_by = jwt_data.get("display_name")

        data = create_transaction_service(
            id_account=payload["id_account"],
            id_category=payload["id_category"],
            transaction_date=payload["transaction_date"],
            transaction_type=payload["transaction_type"],
            amount=payload["amount"],
            transaction_description=payload["transaction_description"],
            reference_number=payload.get("reference_number"),
            attachment_url=payload.get("attachment_url"),
            created_by=created_by
        )

        return success(
            data=data,
            message="Transaction created"
        )


# ===================== #ANCHOR - DETAIL | UPDATE | DELETE =================== #

@ns.route("/<int:id_transaction>")
class TransactionResource(Resource):

    @jwt_required()
    @cashbook_role_required()
    @measure_execution_time
    def get(self, id_transaction):
        """Detail Transaction"""

        data = get_transaction_detail_service(id_transaction)

        if not data:
            raise NotFoundError("Transaction not found")

        return success(data=data, message="Detail transaction")


    @jwt_required()
    @cashbook_role_required()
    @ns.expect(transaction_model)
    @measure_execution_time
    def put(self, id_transaction):
        """Update Transaction"""

        payload = request.get_json()

        updated_by = get_jwt().get("display_name")

        data = update_transaction_service(
            id_transaction=id_transaction,
            id_account=payload["id_account"],
            id_category=payload["id_category"],
            transaction_date=payload["transaction_date"],
            transaction_type=payload["transaction_type"],
            amount=payload["amount"],
            transaction_description=payload["transaction_description"],
            reference_number=payload.get("reference_number"),
            attachment_url=payload.get("attachment_url"),
            updated_by=updated_by
        )

        if not data:
            raise NotFoundError("Transaction not found")

        return success(data=data, message="Transaction updated")


    @jwt_required()
    @cashbook_role_required()
    @measure_execution_time
    def delete(self, id_transaction):
        """Delete Transaction"""

        deleted_by = get_jwt().get("display_name")

        data = delete_transaction_service(
            id_transaction=id_transaction,
            deleted_by=deleted_by
        )

        if not data:
            raise NotFoundError("Transaction not found")

        return success(data=data, message="Transaction deleted")


# =========================== #ANCHOR - BULK CREATE ========================== #

@ns.route("/bulk")
class TransactionBulkResource(Resource):

    @jwt_required()
    @cashbook_role_required()
    @ns.expect([bulk_transaction_model])
    @measure_execution_time
    def post(self):
        """Bulk Create Transaction"""

        payload = request.get_json()

        created_by = get_jwt().get("display_name")

        data = bulk_create_transaction_service(payload, created_by)

        return success(
            data=data,
            message="Bulk transaction created"
        )
# ================== #!SECTION - BASIC OPERATION TRANSACTION ================= #


# ========================= #ANCHOR - ACCOUNT TRANSFER ======================= #

@ns.route("/account-transfer")
class AccountTransferResource(Resource):

    @jwt_required()
    @cashbook_role_required()
    @measure_execution_time
    @ns.expect(account_transfer_model)
    def post(self):
        """Transfer Between Company Accounts"""

        body = request.get_json()

        if body["id_from_account"] == body["id_to_account"]:
            raise ValidationError("Account asal dan tujuan tidak boleh sama.")

        if body["amount"] <= 0:
            raise ValidationError("Nominal transfer harus lebih dari 0.")

        data = account_transfer_service(
            body=body,
            created_by=get_jwt().get("display_name")
        )

        return success(
            data=data,
            message="Transfer antar account berhasil."
        )