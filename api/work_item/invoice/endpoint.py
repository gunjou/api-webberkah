from flask import request
from flask_jwt_extended import jwt_required, get_jwt
from werkzeug.datastructures import FileStorage
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

invoice_create_parser = ns.parser()
invoice_create_parser.add_argument("id_work_item", type=int, required=True, location="form", help="Work Item ID")
invoice_create_parser.add_argument("id_completion", type=int, required=False, location="form", help="ID BA")
invoice_create_parser.add_argument("invoice_number", type=str, required=True, location="form", help="Invoice Number")
invoice_create_parser.add_argument("invoice_date", type=str, required=True, location="form", help="Invoice Date: YYYY-MM-DD")
invoice_create_parser.add_argument("invoice_value", type=float, required=True, location="form", help="Invoice Value")
invoice_create_parser.add_argument("vat_rate", type=float, required=False, location="form", help="VAT Rate")
invoice_create_parser.add_argument("due_date", type=str, required=False, location="form", help="Invoice Due Date: YYYY-MM-DD")
invoice_create_parser.add_argument("notes", type=str, required=False, location="form", help="Notes")
invoice_create_parser.add_argument("document", type=FileStorage, required=False, location="files", help="Invoice Document")

invoice_update_parser = ns.parser()
invoice_update_parser.add_argument("id_work_item", type=int, required=True, location="form", help="Work Item ID")
invoice_update_parser.add_argument("id_completion", type=int, required=False, location="form", help="ID BA")
invoice_update_parser.add_argument("invoice_number", type=str, required=True, location="form", help="Invoice Number")
invoice_update_parser.add_argument("invoice_date", type=str, required=True, location="form", help="Invoice Date: YYYY-MM-DD")
invoice_update_parser.add_argument("invoice_value", type=float, required=True, location="form", help="Invoice Value")
invoice_update_parser.add_argument("vat_rate", type=float, required=False, location="form", help="VAT Rate")
invoice_update_parser.add_argument("due_date", type=str, required=False, location="form", help="Invoice Due Date: YYYY-MM-DD")
invoice_update_parser.add_argument("notes", type=str, required=False, location="form", help="Notes")
invoice_update_parser.add_argument("document", type=FileStorage, required=False, location="files", help="Invoice Document")

invoice_parser = ns.parser()
invoice_parser.add_argument( "stage", type=str, required=False, default="ACTIVE", location="args", choices=("ACTIVE", "CLOSED"), help="Filter stage work item. ACTIVE untuk semua stage selain CLOSED, CLOSED untuk work item yang sudah ditutup.")
invoice_parser.add_argument( "health_status", type=str, required=False, location="args", choices=("PAID", "OVERDUE", "DUE_SOON", "ON_TRACK"), help="Filter berdasarkan kondisi kesehatan invoice.")
invoice_parser.add_argument( "id_client", type=int, required=False, location="args", help="Filter berdasarkan Client.")
invoice_parser.add_argument( "payment_status", type=str, required=False, location="args", choices=("PAID", "UNPAID"), help="Filter berdasarkan status pembayaran.")
invoice_parser.add_argument( "search", type=str, required=False, location="args", help="Cari nomor invoice, nomor work item, nama pekerjaan, atau nama client.")
invoice_parser.add_argument( "page", type=int, required=False, location="args", help="Halaman data. Hanya digunakan ketika stage=CLOSED.")
invoice_parser.add_argument( "per_page", type=int, required=False, location="args", help="Jumlah data per halaman. Hanya digunakan ketika stage=CLOSED.")


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
    @ns.expect(invoice_create_parser)
    @measure_execution_time
    def post(self):
        """Create Work Item Invoice"""

        args = invoice_create_parser.parse_args()

        body = {
            "id_work_item": args.get("id_work_item"),
            "id_completion": args.get("id_completion"),
            "invoice_number": args.get("invoice_number"),
            "invoice_date": args.get("invoice_date"),
            "invoice_value": args.get("invoice_value"),
            "vat_rate": args.get("vat_rate"),
            "due_date": args.get("due_date"),
            "notes": args.get("notes"),
        }

        document = args.get("document")

        created_by = get_jwt().get("display_name")

        data = create_invoice_service(
            body=body,
            created_by=created_by,
            document=document
        )

        return success(
            data=data,
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
    @ns.expect(invoice_update_parser)
    @measure_execution_time
    def put(self, id_invoice):
        """Update Work Item Invoice"""

        args = invoice_update_parser.parse_args()

        body = {
            "id_work_item": args.get("id_work_item"),
            "id_completion": args.get("id_completion"),
            "invoice_number": args.get("invoice_number"),
            "invoice_date": args.get("invoice_date"),
            "invoice_value": args.get("invoice_value"),
            "vat_rate": args.get("vat_rate"),
            "due_date": args.get("due_date"),
            "notes": args.get("notes"),
        }

        document = args.get("document")

        updated_by = get_jwt().get("display_name")

        data = update_invoice_service(
            id_invoice=id_invoice,
            body=body,
            updated_by=updated_by,
            document=document
        )

        return success(
            data=data,
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