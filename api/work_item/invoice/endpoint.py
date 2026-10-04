from flask import request
from flask_jwt_extended import jwt_required, get_jwt
from flask_restx import Resource, fields

from api.shared.response import success
from api.utils.decorator import measure_execution_time

from . import ns
from .service import *


# ======================= #ANCHOR - SWAGGER MODEL ============================ #

invoice_create_model = ns.model(
    "InvoiceCreate",
    {
        "id_work_item": fields.Integer(required=True, description="ID Work Item"),
        "id_completion": fields.Integer(required=False, description="ID BA"),
        "invoice_number": fields.String(required=True, description="Nomor Invoice"),
        "invoice_date": fields.Date(required=True, description="Tanggal Invoice"),
        "invoice_value": fields.Float(required=True, description="Nilai Invoice"),
        "vat_rate": fields.Float(required=False, min=0, max=100, description="Persentase PPN"),
        "due_date": fields.Date(required=False, description="Tanggal jatuh tempo"),
        "document_url": fields.String(required=False, description="URL dokumen Invoice"),
        "notes": fields.String(required=False, description="Catatan")
    }
)

invoice_edit_model = ns.model(
    "InvoiceEdit",
    {
        "id_work_item": fields.Integer(required=True, description="ID Work Item"),
        "id_completion": fields.Integer(required=False, description="ID BA"),
        "invoice_number": fields.String(required=True, description="Nomor Invoice"),
        "invoice_date": fields.Date(required=True, description="Tanggal Invoice"),
        "invoice_value": fields.Float(required=True, description="Nilai Invoice"),
        "vat_rate": fields.Float(required=False, description="Persentase PPN"),
        "due_date": fields.Date(required=False, description="Tanggal jatuh tempo"),
        "document_url": fields.String(required=False, description="URL dokumen Invoice"),
        "notes": fields.String(required=False, description="Catatan")
    }
)

# ======================= #ANCHOR - FILTER PARSER ============================ #

invoice_parser = ns.parser()
invoice_parser.add_argument( "search", type=str, required=False, location="args", help="Cari nomor invoice, nomor work item, nama pekerjaan, atau nama client")
invoice_parser.add_argument( "id_work_item", type=int, required=False, location="args", help="Filter berdasarkan Work Item")
invoice_parser.add_argument( "id_completion", type=int, required=False, location="args", help="Filter berdasarkan BA")
invoice_parser.add_argument( "page", type=int, required=False, default=1, location="args")
invoice_parser.add_argument( "per_page", type=int, required=False, default=10, location="args")


# ============================================================================ #
#                               #SECTION - INVOICE                             #
# ============================================================================ #
@ns.route("")
class InvoiceResource(Resource):

    @jwt_required()
    @ns.expect(invoice_parser)
    @measure_execution_time
    def get(self):
        """List Work Item Invoice"""

        filters = invoice_parser.parse_args()

        data = get_invoice_list_service(filters)

        return success(
            data=data,
            message="Data invoice berhasil diambil"
        )


    @jwt_required()
    @ns.expect(invoice_create_model)
    @measure_execution_time
    def post(self):
        """Create Work Item Invoice"""

        data = request.json or {}

        created_by = get_jwt().get("display_name")

        result = create_invoice_service(
            data=data,
            created_by=created_by
        )

        return success(
            data=result,
            message="Invoice berhasil dibuat"
        )


@ns.route("/<int:id_invoice>")
class InvoiceDetailResource(Resource):

    @jwt_required()
    @measure_execution_time
    def get(self, id_invoice):
        """Detail Work Item Invoice"""

        data = get_invoice_detail_service(id_invoice)

        return success(
            data=data,
            message="Detail invoice berhasil diambil"
        )
    
    
    @jwt_required()
    @ns.expect(invoice_edit_model)
    @measure_execution_time
    def put(self, id_invoice):
        """Edit Work Item Invoice"""

        data = request.json or {}

        updated_by = get_jwt().get("display_name")

        result = update_invoice_service(
            id_invoice=id_invoice,
            data=data,
            updated_by=updated_by
        )

        return success(
            data=result,
            message="Invoice berhasil diperbarui"
        )
    
    
    @jwt_required()
    @measure_execution_time
    def delete(self, id_invoice):
        """Hapus Work Item Invoice"""

        updated_by = get_jwt().get("display_name")

        delete_invoice_service(
            id_invoice=id_invoice,
            updated_by=updated_by
        )

        return success(
            data=None,
            message="Invoice berhasil dihapus"
        )