from flask_jwt_extended import jwt_required
from flask_restx import Namespace, Resource, fields, reqparse
from flask import request

from api.shared.response import success
from api.shared.exceptions import ValidationError, NotFoundError
from api.utils.decorator import measure_execution_time

from api.rcc.invoice.query import *


invoice_ns = Namespace("invoices", description="Invoice Management")

invoice_model = invoice_ns.model(
    "Invoice",
    {
        "id_client": fields.Integer(required=True, description="ID Client"),
        "no_invoice": fields.String(required=True, description="Nomor Invoice"),
        "tanggal_invoice": fields.String(required=True, description="Tanggal Invoice"),
        "tanggal_jatuh_tempo": fields.String(required=True, description="Tanggal Jatuh Tempo"),
        "nilai_invoice": fields.Float(required=True, description="Nilai Invoice"),
        "keterangan": fields.String(required=False)
    }
)

invoice_filter_parser = reqparse.RequestParser()
invoice_filter_parser.add_argument("client", type=int, required=False, location="args", help="ID Client")
invoice_filter_parser.add_argument("payment_status", type=str, required=False, location="args",
    choices=["BELUM_DIBAYAR", "SEBAGIAN_DIBAYAR", "LUNAS"], help="Status Pembayaran"
)
invoice_filter_parser.add_argument("health_status", type=str, required=False, location="args",
    choices=["NORMAL", "PERHATIAN", "TERLAMBAT", "KRITIS"], help="Status Monitoring"
)
invoice_filter_parser.add_argument("start_date", type=str, required=False, location="args", help="Tanggal Invoice Awal (YYYY-MM-DD)")
invoice_filter_parser.add_argument("end_date", type=str, required=False, location="args", help="Tanggal Invoice Akhir (YYYY-MM-DD)")


@invoice_ns.route("")
class InvoiceListResource(Resource):

    @jwt_required()
    @invoice_ns.expect(
        invoice_filter_parser
    )
    @measure_execution_time
    def get(self):
        """List Invoice"""

        args = invoice_filter_parser.parse_args()

        data = get_invoice_list(
            client=args.get("client"),
            payment_status=args.get(
                "payment_status"
            ),
            health_status=args.get(
                "health_status"
            ),
            start_date=args.get(
                "start_date"
            ),
            end_date=args.get(
                "end_date"
            )
        )

        return success(
            data=data,
            message="List invoice"
        )


    @jwt_required()
    @invoice_ns.expect(
        invoice_model,
        validate=True
    )
    @measure_execution_time
    def post(self):
        """Tambah Invoice"""

        body = request.get_json(
            silent=True
        ) or {}

        if not body.get("id_client"):
            raise ValidationError(
                "Client wajib dipilih"
            )

        if not body.get("no_invoice"):
            raise ValidationError(
                "Nomor invoice wajib diisi"
            )

        data = create_invoice(
            id_client=body.get("id_client"),
            no_invoice=body.get("no_invoice"),
            tanggal_invoice=body.get("tanggal_invoice"),
            tanggal_jatuh_tempo=body.get("tanggal_jatuh_tempo"),
            nilai_invoice=body.get("nilai_invoice"),
            keterangan=body.get("keterangan")
        )

        return success(
            data=data,
            message="Invoice berhasil ditambahkan"
        )



@invoice_ns.route("/<int:id_invoice>")
class InvoiceDetailResource(Resource):

    @jwt_required()
    @measure_execution_time
    def get(self, id_invoice):
        """Detail Invoice"""

        invoice = get_invoice_by_id(
            id_invoice
        )

        if not invoice:
            raise NotFoundError(
                "Invoice tidak ditemukan"
            )

        payments = get_invoice_payments(
            id_invoice
        )

        attachments = get_invoice_attachments(
            id_invoice
        )

        return success(
            data={
                "invoice": invoice,
                "payments": payments,
                "attachments": attachments
            },
            message="Detail invoice"
        )


    @jwt_required()
    @invoice_ns.expect(
        invoice_model,
        validate=True
    )
    @measure_execution_time
    def put(self, id_invoice):
        """Update Invoice"""

        existing = get_invoice_by_id(
            id_invoice
        )

        if not existing:
            raise NotFoundError(
                "Invoice tidak ditemukan"
            )

        body = request.get_json(
            silent=True
        ) or {}

        data = update_invoice(
            id_invoice=id_invoice,
            id_client=body.get("id_client"),
            no_invoice=body.get("no_invoice"),
            tanggal_invoice=body.get("tanggal_invoice"),
            tanggal_jatuh_tempo=body.get("tanggal_jatuh_tempo"),
            nilai_invoice=body.get("nilai_invoice"),
            keterangan=body.get("keterangan")
        )

        return success(
            data=data,
            message="Invoice berhasil diperbarui"
        )


    @jwt_required()
    @measure_execution_time
    def delete(self, id_invoice):
        """Delete Invoice"""

        existing = get_invoice_by_id(
            id_invoice
        )

        if not existing:
            raise NotFoundError(
                "Invoice tidak ditemukan"
            )

        delete_invoice(
            id_invoice
        )

        return success(
            message="Invoice berhasil dihapus"
        )