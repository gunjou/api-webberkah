from api.shared.exceptions import ValidationError, NotFoundError

from .query import *


def create_payment_service(payload, created_by):

    id_invoice = payload.get("id_invoice")
    payment_date = payload.get("payment_date")
    amount = payload.get("amount")

    if not id_invoice:
        raise ValidationError("Invoice wajib dipilih")

    if not payment_date:
        raise ValidationError("Tanggal pembayaran wajib diisi")

    if amount is None:
        raise ValidationError("Nominal pembayaran wajib diisi")

    if amount <= 0:
        raise ValidationError("Nominal pembayaran harus lebih besar dari 0")

    return create_payment(
        id_invoice=id_invoice,
        payment_date=payment_date,
        amount=amount,
        document_url=payload.get("document_url"),
        notes=payload.get("notes"),
        created_by=created_by
    )


def get_payment_detail_service(id_payment):

    data = get_payment_detail(id_payment=id_payment)

    if not data:
        raise NotFoundError("Pembayaran tidak ditemukan")

    return data


def delete_payment_service(id_payment, updated_by):

    result = delete_payment(
        id_payment=id_payment,
        updated_by=updated_by
    )

    if not result:
        raise NotFoundError(
            "Pembayaran tidak ditemukan"
        )

    return result