from flask import request
from flask_jwt_extended import jwt_required, get_jwt
from flask_restx import Resource, fields

from api.shared.response import success
from api.shared.exceptions import ValidationError
from api.utils.decorator import measure_execution_time

from . import ns
from .service import *


# ======================= #ANCHOR - SWAGGER MODEL ============================ #

work_item_create_model = ns.model(
    "WorkItemCreate", {
        "work_number": fields.String(required=True, description="Work Number"),
        "work_name": fields.String(required=True, description="Work Name"),
        "work_type": fields.String(required=True, description="Work Type: TENDER / MAINTENANCE"),
        "id_client": fields.Integer(required=True, description="Client ID"),
        "id_client_pic": fields.Integer(required=False, description="Client PIC ID"),
        "internal_pic_name": fields.String(required=False, description="Internal PIC Name"),
        "progress_percent": fields.Float(required=False, description="Initial Progress Percentage"),
        "start_date": fields.Date(required=False, description="Work Start Date"),
        "target_end_date": fields.Date(required=False, description="Target End Date"),
        "notes": fields.String(required=False, description="Work Notes")
    }
)

work_item_update_model = ns.model(
    "WorkItemUpdate", {
        "work_number": fields.String(required=True, description="Work Number"),
        "work_name": fields.String(required=True, description="Work Name"),
        "work_type": fields.String(required=True, description="Work Type: TENDER / MAINTENANCE"),
        "id_client": fields.Integer(required=True, description="Client ID"),
        "id_client_pic": fields.Integer(required=False, description="Client PIC ID"),
        "internal_pic_name": fields.String(required=False, description="Internal PIC Name"),
        "start_date": fields.Date(required=False, description="Work Start Date"),
        "target_end_date": fields.Date(required=False, description="Target End Date"),
        "notes": fields.String(required=False, description="Work Notes")
    }
)


# ======================= #ANCHOR - FILTER PARSER ============================ #

work_item_filter_parser = ns.parser()
work_item_filter_parser.add_argument("search", type=str, required=False, location="args", help="Search by work number or work name.")
work_item_filter_parser.add_argument("work_type", type=str, required=False, choices=("TENDER", "MAINTENANCE"), location="args", help="Filter by work type.")
work_item_filter_parser.add_argument("current_stage", type=str, required=False,
    choices=(
        "IDENTIFIED", "QUOTATION", "CONTRACT", "IN_PROGRESS", "COMPLETED", "BA", "INVOICE", "PAYMENT", "CLOSED"
    ),
    location="args", help="Filter by current stage."
)
work_item_filter_parser.add_argument("id_client", type=int, required=False, location="args", help="Filter by client ID.")
work_item_filter_parser.add_argument("page", type=int, required=False, default=1, location="args", help="Page number.")
work_item_filter_parser.add_argument("per_page", type=int, required=False, default=10, location="args", help="Number of records per page.")


work_item_options_parser = ns.parser()
work_item_options_parser.add_argument(
    "context",
    type=str,
    required=False,
    choices=("quotation", "contract", "invoice", "completion"),
    location="args",
    help="Konteks options: quotation, contract, atau invoice"
)

# ============================================================================ #
#                         #SECTION - WORK ITEM                                #
# ============================================================================ #

@ns.route("")
class WorkItemListResource(Resource):

    @jwt_required()
    @ns.expect(work_item_filter_parser)
    @measure_execution_time
    def get(self):
        """Get Work Item List"""

        filters = work_item_filter_parser.parse_args()

        data = get_work_item_list_service(filters)

        return success(
            data=data,
            message="Data work item berhasil diambil."
        )

    @jwt_required()
    @ns.expect(work_item_create_model)
    @measure_execution_time
    def post(self):
        """Create Work Item"""

        body = request.get_json() or {}
        body["created_by"] = get_jwt().get("display_name")

        id_work_item = create_work_item_service(body)

        return success(
            data={"id_work_item": id_work_item},
            message="Work item berhasil ditambahkan."
        )


@ns.route("/<int:id_work_item>")
class WorkItemDetailResource(Resource):

    @jwt_required()
    @measure_execution_time
    def get(self, id_work_item):
        """Get Work Item Detail"""

        data = get_work_item_detail_service(
            id_work_item
        )

        return success(
            data=data,
            message="Detail work item berhasil diambil."
        )
    
    
    @jwt_required()
    @ns.expect(work_item_update_model)
    @measure_execution_time
    def put(self, id_work_item):
        """Update Work Item"""

        body = request.get_json() or {}

        body["updated_by"] = get_jwt().get("display_name")

        update_work_item_service(
            id_work_item,
            body
        )

        return success(
            data={
                "id_work_item": id_work_item
            },
            message="Work item berhasil diperbarui."
        )
    
    
    @jwt_required()
    @measure_execution_time
    def delete(self, id_work_item):
        """Delete Work Item"""

        delete_work_item_service(
            id_work_item,
            get_jwt().get("display_name")
        )

        return success(
            data={
                "id_work_item": id_work_item
            },
            message="Work item berhasil dinonaktifkan."
        )


@ns.route("/options")
class WorkItemOptionsResource(Resource):

    @jwt_required()
    @ns.expect(work_item_options_parser)
    @measure_execution_time
    def get(self):
        """Work Item Options"""

        args = work_item_options_parser.parse_args()

        data = get_work_item_options_service(
            context=args.get("context")
        )

        return success(
            data=data,
            message="Opsi work item berhasil diambil"
        )
