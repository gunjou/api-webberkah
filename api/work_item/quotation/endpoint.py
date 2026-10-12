from flask import request
from flask_jwt_extended import jwt_required, get_jwt
from werkzeug.datastructures import FileStorage
from flask_restx import Resource, fields

from api.shared.response import success
from api.utils.decorator import measure_execution_time

from . import ns
from .service import *


# ======================= #ANCHOR - SWAGGER MODEL ============================ #

quotation_create_model = ns.model(
    "QuotationCreate", {
        "id_work_item": fields.Integer(required=True, description="Work Item ID"),
        "proposal_number": fields.String(required=True, description="Quotation Number"),
        "proposal_date": fields.Date(required=True, description="Quotation Date"),
        "proposal_value": fields.Float(required=False, description="Quotation Value"),
        "valid_until": fields.Date(required=False, description="Quotation Valid Until"),
        "status": fields.String(
            required=False,
            description=(
                "Quotation Status: "
                "DRAFT / SUBMITTED / WON / LOST / "
                "EXPIRED / CANCELLED"
            )
        ),
        "notes": fields.String(required=False, description="Quotation Notes")
    }
)

quotation_update_model = ns.model(
    "QuotationUpdate", {
        "id_work_item": fields.Integer(required=True, description="Work Item ID"),
        "proposal_number": fields.String(required=True, description="Quotation Number"),
        "proposal_date": fields.Date(required=True, description="Quotation Date"),
        "proposal_value": fields.Float(required=False, description="Quotation Value"),
        "valid_until": fields.Date(required=False, description="Quotation Valid Until"),
        "status": fields.String(required=False, enum=["DRAFT", "SUBMITTED", "WON", "LOST", "EXPIRED", "CANCELLED"]),
        "notes": fields.String(required=False, description="Quotation Notes")
    }
)


# ======================= #ANCHOR - FILTER PARSER ============================ #

quotation_create_parser = ns.parser()
quotation_create_parser.add_argument("id_work_item", type=int, required=True, location="form", help="Work Item ID")
quotation_create_parser.add_argument("proposal_number", type=str, required=True, location="form", help="Quotation Number")
quotation_create_parser.add_argument("proposal_date", type=str, required=True, location="form", help="Quotation Date: YYYY-MM-DD")
quotation_create_parser.add_argument("proposal_value", type=float, required=False, location="form", help="Quotation Value")
quotation_create_parser.add_argument("valid_until", type=str, required=False, location="form", help="Quotation Valid Until: YYYY-MM-DD")
quotation_create_parser.add_argument("status", type=str, required=False, location="form", help="Quotation Status: DRAFT / SUBMITTED / WON / LOST / EXPIRED / CANCELLED")
quotation_create_parser.add_argument("notes", type=str, required=False, location="form", help="Quotation Notes")
quotation_create_parser.add_argument("document", type=FileStorage, required=False, location="files", help="Quotation Document")

quotation_update_parser = ns.parser()
quotation_update_parser.add_argument("id_work_item", type=int, required=True, location="form", help="Work Item ID")
quotation_update_parser.add_argument("proposal_number", type=str, required=True, location="form", help="Quotation Number")
quotation_update_parser.add_argument("proposal_date", type=str, required=True, location="form", help="Quotation Date: YYYY-MM-DD")
quotation_update_parser.add_argument("proposal_value", type=float, required=False, location="form", help="Quotation Value")
quotation_update_parser.add_argument("valid_until", type=str, required=False, location="form", help="Quotation Valid Until: YYYY-MM-DD")
quotation_update_parser.add_argument("status", type=str, required=False, location="form", help="Quotation Status: DRAFT / SUBMITTED / WON / LOST / EXPIRED / CANCELLED")
quotation_update_parser.add_argument("notes", type=str, required=False, location="form", help="Quotation Notes")
quotation_update_parser.add_argument("document", type=FileStorage, required=False, location="files", help="Quotation Document")

quotation_filter_parser = ns.parser()
quotation_filter_parser.add_argument("stage", type=str, required=False, default="ACTIVE", choices=("ACTIVE", "CLOSED"), location="args", help="Filter berdasarkan status quotation. ACTIVE untuk quotation aktif, CLOSED untuk quotation yang sudah ditutup/dihapus.")
quotation_filter_parser.add_argument("status", type=str, required=False, choices=("DRAFT", "SUBMITTED", "WON", "LOST", "EXPIRED", "CANCELLED"), location="args", help="Filter berdasarkan quotation status.")
quotation_filter_parser.add_argument("search", type=str, required=False, location="args", help="Search by quotation number.")
quotation_filter_parser.add_argument("id_work_item", type=int, required=False, location="args", help="Filter by work item ID.")
quotation_filter_parser.add_argument("id_client", type=int, required=False, location="args", help="Filter by client ID.")
quotation_filter_parser.add_argument("page", type=int, required=False, location="args", help="Page number. Only used when stage=CLOSED.")
quotation_filter_parser.add_argument("per_page", type=int, required=False, location="args", help="Number of records per page. Minimum 25 and only used when stage=CLOSED.")

# ============================================================================ #
#                         #SECTION - QUOTATION                                 #
# ============================================================================ #

@ns.route("")
class QuotationListResource(Resource):

    @jwt_required()
    @ns.expect(quotation_filter_parser)
    @measure_execution_time
    def get(self):
        """Get Quotation List"""

        filters = quotation_filter_parser.parse_args()

        data = get_quotation_list_service(filters)

        return success(
            data=data,
            message="Data penawaran berhasil diambil."
        )


    @jwt_required()
    @ns.expect(quotation_create_parser)
    @measure_execution_time
    def post(self):
        """Create Quotation"""

        args = quotation_create_parser.parse_args()

        body = {
            "id_work_item": args.get("id_work_item"),
            "proposal_number": args.get("proposal_number"),
            "proposal_date": args.get("proposal_date"),
            "proposal_value": args.get("proposal_value"),
            "valid_until": args.get("valid_until"),
            "status": args.get("status"),
            "notes": args.get("notes"),
            "created_by": get_jwt().get("display_name"),
        }

        document = args.get("document")

        # Validasi bisnis + upload + create
        id_proposal = create_quotation_service(
            body,
            document=document,
        )

        return success(
            data={
                "id_proposal": id_proposal
            },
            message="Penawaran berhasil ditambahkan."
        )


@ns.route("/<int:id_proposal>")
class QuotationDetailResource(Resource):

    @jwt_required()
    @measure_execution_time
    def get(self, id_proposal):
        """Detail Work Item Quotation"""

        quotation = get_quotation_detail_service(id_proposal)

        return success(
            data=quotation,
            message="Detail penawaran berhasil diambil"
        )
    
    
    @jwt_required()
    @ns.expect(quotation_update_parser)
    @measure_execution_time
    def put(self, id_proposal):
        """Update Work Item Quotation"""

        args = quotation_update_parser.parse_args()

        body = {
            "id_work_item": args.get("id_work_item"),
            "proposal_number": args.get("proposal_number"),
            "proposal_date": args.get("proposal_date"),
            "proposal_value": args.get("proposal_value"),
            "valid_until": args.get("valid_until"),
            "status": args.get("status"),
            "notes": args.get("notes"),
        }

        document = args.get("document")

        updated_by = get_jwt().get("display_name")

        data = update_quotation_service(
            id_proposal=id_proposal,
            body=body,
            updated_by=updated_by,
            document=document,
        )

        return success(
            data=data,
            message="Penawaran berhasil diperbarui"
        )
    
    
    @jwt_required()
    @measure_execution_time
    def delete(self, id_proposal):
        """Delete Quotation"""

        updated_by = get_jwt().get("display_name")

        delete_quotation_service(
            id_proposal=id_proposal,
            updated_by=updated_by
        )

        return success(
            data=None,
            message="Penawaran berhasil dihapus."
        )