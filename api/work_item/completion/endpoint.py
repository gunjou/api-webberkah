from flask import request
from flask_jwt_extended import jwt_required, get_jwt
from flask_restx import Resource, fields

from api.shared.response import success
from api.utils.decorator import measure_execution_time

from . import ns
from .service import *


# ======================= #ANCHOR - SWAGGER MODEL ============================ #

completion_create_model = ns.model(
    "CompletionCreate",
    {
        "id_work_item": fields.Integer(required=True, description="Work Item ID"),
        "ba_number": fields.String(required=True, description="BA Number"),
        "ba_date": fields.Date(required=True, description="BA Date"),
        "completion_date": fields.Date(required=False, description="Completion Date"),
        "document_url": fields.String(required=False, description="BA Document URL"),
        "notes": fields.String(required=False, description="Notes")
    }
)

completion_edit_model = ns.model(
    "CompletionEdit",
    {
        "id_work_item": fields.Integer(required=True, description="ID Work Item"),
        "ba_number": fields.String(required=True, description="Nomor BA"),
        "ba_date": fields.Date(required=True, description="Tanggal BA"),
        "completion_date": fields.Date(required=False, description="Tanggal penyelesaian pekerjaan"),
        "document_url": fields.String(required=False, description="URL dokumen BA"),
        "notes": fields.String(required=False, description="Catatan")
    }
)


# ======================= #ANCHOR - FILTER PARSER ============================ #

completion_filter_parser = ns.parser()
completion_filter_parser.add_argument( "search", type=str, required=False, location="args")
completion_filter_parser.add_argument( "id_work_item", type=int, required=False, location="args")
completion_filter_parser.add_argument( "page", type=int, required=False, default=1, location="args")
completion_filter_parser.add_argument( "per_page", type=int, required=False, default=10, location="args")

completion_options_parser = ns.parser()
completion_options_parser.add_argument("context", type=str, required=False, choices=("invoice"), location="args", help="Konteks options: invoice")

# ============================================================================ #
#                           #SECTION - COMPLETION (BA)                         #
# ============================================================================ #
@ns.route("")
class CompletionListResource(Resource):

    @jwt_required()
    @ns.expect(completion_filter_parser)
    @measure_execution_time
    def get(self):
        """List Work Item Completion / BA"""

        filters = completion_filter_parser.parse_args()

        data = get_completion_list_service(filters)

        return success(
            data=data,
            message="Data BA berhasil diambil"
        )

    @jwt_required()
    @ns.expect(completion_create_model)
    @measure_execution_time
    def post(self):
        """Create Work Item Completion / BA"""

        body = request.json or {}
        created_by = get_jwt().get("display_name")

        data = create_completion_service(
            body=body,
            created_by=created_by
        )

        return success(
            data=data,
            message="BA berhasil dibuat"
        )


@ns.route("/<int:id_completion>")
class CompletionDetailResource(Resource):

    @jwt_required()
    @measure_execution_time
    def get(self, id_completion):
        """Detail Work Item Completion / BA"""

        data = get_completion_detail_service(id_completion)

        return success(
            data=data,
            message="Detail BA berhasil diambil"
        )
    
    
    @jwt_required()
    @ns.expect(completion_edit_model)
    @measure_execution_time
    def put(self, id_completion):
        """Edit Work Item Completion / BA"""

        data = request.json or {}

        updated_by = get_jwt().get("display_name")

        result = update_completion_service(
            id_completion=id_completion,
            data=data,
            updated_by=updated_by
        )

        return success(
            data=result,
            message="BA berhasil diperbarui"
        )
    
    
    @jwt_required()
    @measure_execution_time
    def delete(self, id_completion):
        """Hapus Work Item Completion / BA"""

        updated_by = get_jwt().get("display_name")

        delete_completion_service(
            id_completion=id_completion,
            updated_by=updated_by
        )

        return success(
            data=None,
            message="BA berhasil dihapus"
        )


@ns.route("/options")
class CompletionOptionsResource(Resource):

    @jwt_required()
    @ns.expect(completion_options_parser)
    @measure_execution_time
    def get(self):
        """Completion Options"""

        args = completion_options_parser.parse_args()

        data = get_completion_options_service(
            context=args.get("context")
        )

        return success(
            data=data,
            message="Opsi BA berhasil diambil"
        )