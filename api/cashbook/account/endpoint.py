# api/cashbook/category/endpoint.py
from flask import request
from flask_jwt_extended import jwt_required, get_jwt

from flask_restx import Resource, fields

from api.shared.response import success
from api.shared.exceptions import ValidationError, NotFoundError
from api.utils.decorator import measure_execution_time
from api.security.cashbook import cashbook_role_required

from . import ns
from .query import *


# ============================================================================ #
#                            #ANCHOR - SWAGGER MODEL                           #
# ============================================================================ #
account_model = ns.model(
    "Account", {
        "account_name": fields.String(required=True,description="Nama Account"),
        "account_kind": fields.String(required=True,description="Jenis Account (BANK/CASH/EWALLET)"),
        "bank_name": fields.String(required=False),
        "account_type": fields.String(required=False),
        "branch_name": fields.String(required=False),
        "account_number": fields.String(required=False),
        "account_holder": fields.String(required=False)
    }
)


# ============================================================================ #
#                      #SECTION - BASIC OPERATION ACCOUNT                      #
# ============================================================================ #

# ================= #ANCHOR - GET LIST ACCOUNT & POST ACCOUNT ================ #

@ns.route("")
class AccountListResource(Resource):

    @jwt_required()
    @cashbook_role_required()
    @measure_execution_time
    def get(self):
        """List Account"""

        data = get_account_list()

        return success(
            data=data,
            message="List account"
        )

    @jwt_required()
    @cashbook_role_required()
    @measure_execution_time
    @ns.expect(account_model)
    def post(self):
        """Create Account"""

        body = request.get_json()

        if not body.get("account_name"):
            raise ValidationError("Nama account wajib diisi.")

        if not body.get("account_kind"):
            raise ValidationError("Jenis account wajib diisi.")

        id_account = create_account(
            account_name=body["account_name"],
            account_kind=body["account_kind"],
            bank_name=body.get("bank_name"),
            account_type=body.get("account_type"),
            branch_name=body.get("branch_name"),
            account_number=body.get("account_number"),
            account_holder=body.get("account_holder"),
            created_by=get_jwt().get("display_name")
        )

        return success(
            data={"id_account": id_account},
            message="Account berhasil ditambahkan."
        )


# ============== #ANCHOR - DETAIL ACCOUNT (GET | UPDATE | DELETE) ============ #
@ns.route("/<int:id_account>")
class AccountResource(Resource):

    @jwt_required()
    @cashbook_role_required()
    @measure_execution_time
    def get(self, id_account):
        """Detail Account"""

        data = get_account_detail(id_account)

        if not data:
            raise NotFoundError("Account tidak ditemukan.")

        return success(data=data, message="Detail account")


    @jwt_required()
    @cashbook_role_required()
    @measure_execution_time
    @ns.expect(account_model)
    def put(self, id_account):
        """Update Account"""

        body = request.get_json()

        if not body.get("account_name"):
            raise ValidationError("Nama account wajib diisi.")

        if not body.get("account_kind"):
            raise ValidationError("Jenis account wajib diisi.")

        affected = update_account(
            id_account=id_account,
            account_name=body["account_name"],
            account_kind=body["account_kind"],
            bank_name=body.get("bank_name"),
            account_type=body.get("account_type"),
            branch_name=body.get("branch_name"),
            account_number=body.get("account_number"),
            account_holder=body.get("account_holder"),
            updated_by=get_jwt().get("display_name")
        )

        if affected == 0:
            raise NotFoundError("Account tidak ditemukan.")

        return success(message="Account berhasil diperbarui.")


    @jwt_required()
    @cashbook_role_required()
    @measure_execution_time
    def delete(self, id_account):
        """Delete Account"""

        affected = delete_account(
            id_account=id_account,
            deleted_by=get_jwt().get("display_name")
        )

        if affected == 0:
            raise NotFoundError("Account tidak ditemukan.")

        return success(message="Account berhasil dihapus.")


@ns.route("/dropdown")
class AccountDropdownResource(Resource):

    @jwt_required()
    @cashbook_role_required()
    @measure_execution_time
    def get(self):
        """Dropdown Account"""
        return success(data=get_account_dropdown(), message="Dropdown account")
    
# ==================== #!SECTION - BASIC OPERATION ACCOUNT =================== #