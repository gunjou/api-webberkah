# api/cashbook/opening_balance/endpoint.py
from flask import request
from flask_jwt_extended import jwt_required, get_jwt
from flask_restx import Resource, fields

from api.shared.response import success
from api.shared.exceptions import ValidationError, NotFoundError
from api.utils.decorator import measure_execution_time
from api.security.cashbook import cashbook_role_required

from . import ns
from .service import *


# ======================= #ANCHOR - SWAGGER MODEL ============================ #

opening_balance_model = ns.model(
    "OpeningBalance", {
        "id_account": fields.Integer(required=True, description="Account ID"),
        "effective_date": fields.String(required=True, description="Effective Date"),
        "opening_balance": fields.Float(required=True, description="Opening Balance"),
        "notes": fields.String(required=False, description="Notes")
    }
)

generate_opening_balance_model = ns.model(
    "GenerateOpeningBalance", {
        "effective_date": fields.String(required=True, description="Effective Date"),
        "notes": fields.String(required=False, description="Checkpoint Notes")
    }
)


# ======================= #ANCHOR - FILTER PARSER ============================ #

opening_balance_filter_parser = ns.parser()
opening_balance_filter_parser.add_argument("id_account", type=int, required=False)
opening_balance_filter_parser.add_argument("effective_date", type=str, required=False)


# ============================================================================ #
#                   #SECTION - BASIC OPERATION OPENING BALANCE                 #
# ============================================================================ #

# ================= #ANCHOR - GET & POST LIST OPENING BALANCE ================ #

@ns.route("")
class OpeningBalanceListResource(Resource):

    @jwt_required()
    @cashbook_role_required()
    @ns.expect(opening_balance_filter_parser)
    @measure_execution_time
    def get(self):
        """List Opening Balance"""

        filters = request.args.to_dict()

        data = get_opening_balance_list_service(filters)

        return success(
            data=data,
            message="List opening balance"
        )

    @jwt_required()
    @cashbook_role_required()
    @ns.expect(opening_balance_model)
    @measure_execution_time
    def post(self):
        """Create Opening Balance"""

        body = request.get_json()

        if body["opening_balance"] < 0:
            raise ValidationError("Opening balance tidak boleh bernilai negatif.")

        body["created_by"] = get_jwt().get("display_name")

        id_opening_balance = create_opening_balance_service(body)

        return success(
            data={"id_opening_balance": id_opening_balance},
            message="Opening balance berhasil ditambahkan."
        )

# ================ #!SECTION - BASIC OPERATION OPENING BALANCE =============== #



# ============================================================================ #
#                  #SECTION - UPDATE OPERATION OPENING BALANCE                 #
# ============================================================================ #

# ======================= #ANCHOR - UPDATE OPENING BALANCE =================== #

@ns.route("/<int:id_opening_balance>")
class OpeningBalanceResource(Resource):
    
    @jwt_required()
    @cashbook_role_required()
    @measure_execution_time
    def get(self, id_opening_balance):
        """Detail Opening Balance"""

        data = get_opening_balance_detail_service(id_opening_balance)

        return success(
            data=data,
            message="Detail opening balance"
        )

    @jwt_required()
    @cashbook_role_required()
    @ns.expect(opening_balance_model)
    @measure_execution_time
    def put(self, id_opening_balance):
        """Update Opening Balance"""

        body = request.get_json()

        if body["opening_balance"] < 0:
            raise ValidationError("Opening balance tidak boleh bernilai negatif.")

        body["updated_by"] = get_jwt().get("display_name")

        update_opening_balance_service(
            id_opening_balance=id_opening_balance,
            body=body
        )

        return success(message="Opening balance berhasil diperbarui.")

# ================ #!SECTION - UPDATE OPERATION OPENING BALANCE ============== #



# ============================================================================ #
#                 #SECTION - GENERATE OPERATION OPENING BALANCE                #
# ============================================================================ #

# ===================== #ANCHOR - GENERATE OPENING BALANCE =================== #

@ns.route("/generate")
class OpeningBalanceGenerateResource(Resource):

    @jwt_required()
    @cashbook_role_required()
    @ns.expect(generate_opening_balance_model)
    @measure_execution_time
    def post(self):
        """Generate Opening Balance"""

        body = request.get_json()

        if not body.get("effective_date"):
            raise ValidationError("Effective date wajib diisi.")

        body["created_by"] = get_jwt().get("display_name")

        data = generate_opening_balance_service(
            body
        )

        return success(
            data=data,
            message="Opening balance berhasil digenerate."
        )

# =============== #!SECTION - GENERATE OPERATION OPENING BALANCE ============= #


@ns.route("/display")
class OpeningBalanceDisplayResource(Resource):

    @jwt_required()
    @cashbook_role_required()
    @measure_execution_time
    def get(self):
        """Display Opening Balance"""

        return success(
            data=get_opening_balance_display_service(),
            message="Display opening balance"
        )