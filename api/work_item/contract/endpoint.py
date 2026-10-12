from flask import request
from flask_jwt_extended import jwt_required, get_jwt
from werkzeug.datastructures import FileStorage
from flask_restx import Resource, fields

from api.shared.response import success
from api.utils.decorator import measure_execution_time

from . import ns
from .service import *


# ======================= #ANCHOR - SWAGGER MODEL ============================ #

contract_create_model = ns.model(
    "ContractCreate",
    {
        "id_work_item": fields.Integer(required=True, description="Work Item ID"),
        "contract_number": fields.String(required=True, description="Contract Number"),
        "contract_date": fields.Date(required=True, description="Contract Date"),
        "start_date": fields.Date(required=False, description="Contract Start Date"),
        "end_date": fields.Date(required=False, description="Contract End Date"),
        "contract_value": fields.Float(required=False, description="Contract Value"),
        "vat_rate": fields.Float(required=False, description="VAT Rate"),
        "status": fields.String(required=False, enum=["ACTIVE", "COMPLETED", "CANCELLED"], description="Contract Status"),
        "notes": fields.String(required=False, description="Notes")
    }
)


contract_update_model = ns.model(
    "ContractUpdate",
    {
        "id_work_item": fields.Integer(required=True, description="Work Item ID"),
        "contract_number": fields.String(required=True, description="Contract Number"),
        "contract_date": fields.Date(required=True, description="Contract Date"),
        "start_date": fields.Date(required=False, description="Contract Start Date"),
        "end_date": fields.Date(required=False, description="Contract End Date"),
        "contract_value": fields.Float(required=False, description="Contract Value"),
        "vat_rate": fields.Float(required=False, description="VAT Rate"),
        "status": fields.String(required=False, enum=["ACTIVE", "COMPLETED", "CANCELLED"], description="Contract Status"),
        "notes": fields.String(required=False, description="Notes")
    }
)


# ======================= #ANCHOR - FILTER PARSER ============================ #

contract_create_parser = ns.parser()
contract_create_parser.add_argument("id_work_item", type=int, required=True, location="form", help="Work Item ID")
contract_create_parser.add_argument("contract_number", type=str, required=True, location="form", help="Contract Number")
contract_create_parser.add_argument("contract_date", type=str, required=True, location="form", help="Contract Date: YYYY-MM-DD")
contract_create_parser.add_argument("start_date", type=str, required=False, location="form", help="Contract Start Date: YYYY-MM-DD")
contract_create_parser.add_argument("end_date", type=str, required=False, location="form", help="Contract End Date: YYYY-MM-DD")
contract_create_parser.add_argument("contract_value", type=float, required=False, location="form", help="Contract Value")
contract_create_parser.add_argument("vat_rate", type=float, required=False, location="form", help="VAT Rate")
contract_create_parser.add_argument("status", type=str, required=False, location="form", help="Contract Status: ACTIVE / COMPLETED / CANCELLED")
contract_create_parser.add_argument("notes", type=str, required=False, location="form", help="Notes")
contract_create_parser.add_argument("document", type=FileStorage, required=False, location="files", help="Contract Document")

contract_update_parser = ns.parser()
contract_update_parser.add_argument("id_work_item", type=int, required=True, location="form", help="Work Item ID")
contract_update_parser.add_argument("contract_number", type=str, required=True, location="form", help="Contract Number")
contract_update_parser.add_argument("contract_date", type=str, required=True, location="form", help="Contract Date: YYYY-MM-DD")
contract_update_parser.add_argument("start_date", type=str, required=False, location="form", help="Contract Start Date: YYYY-MM-DD")
contract_update_parser.add_argument("end_date", type=str, required=False, location="form", help="Contract End Date: YYYY-MM-DD")
contract_update_parser.add_argument("contract_value", type=float, required=False, location="form", help="Contract Value")
contract_update_parser.add_argument("vat_rate", type=float, required=False, location="form", help="VAT Rate")
contract_update_parser.add_argument("status", type=str, required=False, location="form", help="Contract Status: ACTIVE / COMPLETED / CANCELLED")
contract_update_parser.add_argument("notes", type=str, required=False, location="form", help="Notes")
contract_update_parser.add_argument("document", type=FileStorage, required=False, location="files", help="Contract Document")

contract_filter_parser = ns.parser()
contract_filter_parser.add_argument("stage", type=str, required=False, default="ACTIVE", choices=("ACTIVE", "CLOSED"), location="args", help="Filter berdasarkan stage Work Item. ACTIVE untuk semua stage selain CLOSED, CLOSED untuk Work Item yang sudah ditutup.")
contract_filter_parser.add_argument("status", type=str, required=False, choices=("ACTIVE", "COMPLETED", "CANCELLED"), location="args", help="Filter berdasarkan status contract.")
contract_filter_parser.add_argument("health_status", type=str, required=False, choices=("COMPLETED", "EXPIRED", "DUE_SOON", "ON_TRACK", "NO_DATE"), location="args", help="Filter berdasarkan kondisi kesehatan contract.")
contract_filter_parser.add_argument("search", type=str, required=False, location="args", help="Search by contract number, work number, work name, or client name.")
contract_filter_parser.add_argument("id_work_item", type=int, required=False, location="args", help="Filter by work item ID.")
contract_filter_parser.add_argument("id_client", type=int, required=False, location="args", help="Filter by client ID.")
contract_filter_parser.add_argument("page", type=int, required=False, location="args", help="Page number. Only used when stage=CLOSED.")
contract_filter_parser.add_argument("per_page", type=int, required=False, location="args", help="Number of records per page. Minimum 25 and only used when stage=CLOSED.")


# ============================================================================ #
#                              #SECTION - CONTRACT                             #
# ============================================================================ #

@ns.route("")
class ContractListResource(Resource):

    @jwt_required()
    @ns.expect(contract_filter_parser)
    @measure_execution_time
    def get(self):
        """List Work Item Contract"""

        filters = contract_filter_parser.parse_args()

        data = get_contract_list_service(filters)

        return success(
            data=data,
            message="Data kontrak berhasil diambil"
        )


    @jwt_required()
    @ns.expect(contract_create_parser)
    @measure_execution_time
    def post(self):
        """Create Work Item Contract"""

        args = contract_create_parser.parse_args()

        body = {
            "id_work_item": args.get("id_work_item"),
            "contract_number": args.get("contract_number"),
            "contract_date": args.get("contract_date"),
            "start_date": args.get("start_date"),
            "end_date": args.get("end_date"),
            "contract_value": args.get("contract_value"),
            "vat_rate": args.get("vat_rate"),
            "status": args.get("status"),
            "notes": args.get("notes"),
        }

        document = args.get("document")

        created_by = get_jwt().get("display_name")

        data = create_contract_service(
            body=body,
            created_by=created_by,
            document=document
        )

        return success(
            data=data,
            message="Kontrak berhasil dibuat"
        )


@ns.route("/<int:id_contract>")
class ContractDetailResource(Resource):

    @jwt_required()
    @measure_execution_time
    def get(self, id_contract):
        """Detail Work Item Contract"""

        data = get_contract_detail_service(id_contract)

        return success(
            data=data,
            message="Detail kontrak berhasil diambil"
        )
    
    
    @jwt_required()
    @ns.expect(contract_update_parser)
    @measure_execution_time
    def put(self, id_contract):
        """Update Work Item Contract"""

        args = contract_update_parser.parse_args()

        body = {
            "id_work_item": args.get("id_work_item"),
            "contract_number": args.get("contract_number"),
            "contract_date": args.get("contract_date"),
            "start_date": args.get("start_date"),
            "end_date": args.get("end_date"),
            "contract_value": args.get("contract_value"),
            "vat_rate": args.get("vat_rate"),
            "status": args.get("status"),
            "notes": args.get("notes"),
        }

        document = args.get("document")

        updated_by = get_jwt().get("display_name")

        data = update_contract_service(
            id_contract=id_contract,
            body=body,
            updated_by=updated_by,
            document=document
        )

        return success(
            data=data,
            message="Kontrak berhasil diperbarui"
        )
    
    
    @jwt_required()
    @measure_execution_time
    def delete(self, id_contract):
        """Delete Work Item Contract"""

        created_by = get_jwt().get("display_name")

        delete_contract_service(
            id_contract=id_contract,
            updated_by=created_by
        )

        return success(
            message="Kontrak berhasil dihapus."
        )
