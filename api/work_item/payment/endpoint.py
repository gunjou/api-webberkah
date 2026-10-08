from flask_jwt_extended import jwt_required, get_jwt
from flask_restx import Resource, fields

from api.shared.response import success
from api.utils.decorator import measure_execution_time

from . import ns
from .service import *


# ================================= PAYMENT MODEL ================================= #

payment_model = ns.model(
    "PaymentCreate",
    {
        "id_invoice": fields.Integer(required=True, description="ID invoice"),
        "payment_date": fields.Date(required=True, description="Tanggal pembayaran"),
        "amount": fields.Float(required=True, description="Nominal pembayaran"),
        "document_url": fields.String(required=False, description="URL dokumen bukti pembayaran"),
        "notes": fields.String(required=False, description="Catatan pembayaran")
    }
)


# ================================= PAYMENT RESOURCE =============================== #

@ns.route("")
class PaymentResource(Resource):

    @jwt_required()
    @ns.expect(payment_model)
    @measure_execution_time
    def post(self):
        """Create Work Item Payment"""

        payload = ns.payload

        created_by = get_jwt().get("display_name")

        data = create_payment_service(
            payload=payload,
            created_by=created_by
        )

        return success(
            data=data,
            message="Pembayaran berhasil ditambahkan"
        )


# ================================ PAYMENT DETAIL ================================= #

@ns.route("/<int:id_payment>")
class PaymentDetailResource(Resource):

    @jwt_required()
    @measure_execution_time
    def get(self, id_payment):
        """Get Work Item Payment Detail"""

        data = get_payment_detail_service(
            id_payment=id_payment
        )

        return success(
            data=data,
            message="Detail pembayaran berhasil diambil"
        )
    
    
    @jwt_required()
    @measure_execution_time
    def delete(self, id_payment):
        """Hapus Work Item Payment"""

        updated_by = get_jwt().get("display_name")

        delete_payment_service(
            id_payment=id_payment,
            updated_by=updated_by
        )

        return success(
            data=None,
            message="Pembayaran berhasil dihapus"
        )