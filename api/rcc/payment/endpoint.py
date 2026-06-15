from flask import request
from flask_jwt_extended import jwt_required
from flask_restx import Namespace, Resource, fields

from api.shared.response import success
from api.shared.exceptions import ValidationError, NotFoundError
from api.utils.decorator import measure_execution_time
from api.rcc.payment.query import *


payment_ns = Namespace("payments", description="Payment Management")

payment_model = payment_ns.model(
    "Payment",
    {
        "tanggal_bayar": fields.String(required=True, description="Tanggal Pembayaran"),
        "jumlah_bayar": fields.Float(required=True, description="Jumlah Pembayaran"),
        "metode_bayar": fields.String(required=False),
        "nomor_referensi": fields.String(required=False),
        "keterangan": fields.String(required=False)
    }
)


@payment_ns.route(
    "/invoices/<int:id_invoice>/payments"
)
class PaymentListResource(Resource):

    @jwt_required()
    @measure_execution_time
    def get(self, id_invoice):
        """List Payment"""

        data = get_payment_list(
            id_invoice
        )

        return success(
            data=data,
            message="List payment"
        )

    @jwt_required()
    @payment_ns.expect(
        payment_model,
        validate=True
    )
    @measure_execution_time
    def post(self, id_invoice):
        """Tambah Payment"""

        body = request.get_json(
            silent=True
        ) or {}

        if not body.get(
            "tanggal_bayar"
        ):
            raise ValidationError(
                "Tanggal bayar wajib diisi"
            )

        if not body.get(
            "jumlah_bayar"
        ):
            raise ValidationError(
                "Jumlah bayar wajib diisi"
            )

        data = create_payment(
            id_invoice=id_invoice,
            tanggal_bayar=body.get(
                "tanggal_bayar"
            ),
            jumlah_bayar=body.get(
                "jumlah_bayar"
            ),
            metode_bayar=body.get(
                "metode_bayar"
            ),
            nomor_referensi=body.get(
                "nomor_referensi"
            ),
            keterangan=body.get(
                "keterangan"
            )
        )

        return success(
            data=data,
            message="Payment berhasil ditambahkan"
        )


@payment_ns.route(
    "/<int:id_payment>"
)
class PaymentDetailResource(Resource):

    @jwt_required()
    @measure_execution_time
    def get(
        self,
        id_payment
    ):
        """Detail Payment"""

        data = get_payment_by_id(
            id_payment
        )

        if not data:
            raise NotFoundError(
                "Payment tidak ditemukan"
            )

        return success(
            data=data,
            message="Detail payment"
        )


    @jwt_required()
    @payment_ns.expect(
        payment_model,
        validate=True
    )
    @measure_execution_time
    def put(
        self,
        id_payment
    ):
        """Update Payment"""

        existing = (
            get_payment_by_id(
                id_payment
            )
        )

        if not existing:
            raise NotFoundError(
                "Payment tidak ditemukan"
            )

        body = request.get_json(
            silent=True
        ) or {}

        data = update_payment(
            id_payment=id_payment,
            tanggal_bayar=body.get(
                "tanggal_bayar"
            ),
            jumlah_bayar=body.get(
                "jumlah_bayar"
            ),
            metode_bayar=body.get(
                "metode_bayar"
            ),
            nomor_referensi=body.get(
                "nomor_referensi"
            ),
            keterangan=body.get(
                "keterangan"
            )
        )

        return success(
            data=data,
            message="Payment berhasil diperbarui"
        )


    @jwt_required()
    @measure_execution_time
    def delete(
        self,
        id_payment
    ):
        """Delete Payment"""

        existing = (
            get_payment_by_id(
                id_payment
            )
        )

        if not existing:
            raise NotFoundError(
                "Payment tidak ditemukan"
            )

        delete_payment(
            id_payment
        )

        return success(
            message="Payment berhasil dihapus"
        )