from sqlalchemy import text
from api.utils.config import engine


# ==================================================
# LIST PAYMENT
# ==================================================
def get_payment_list(id_invoice: int):
    sql = text("""
        SELECT
            id_payment,
            id_invoice,
            tanggal_bayar,
            jumlah_bayar,
            metode_bayar,
            nomor_referensi,
            keterangan,
            created_at,
            updated_at
        FROM payments
        WHERE id_invoice = :id_invoice
          AND status = 1
        ORDER BY
            tanggal_bayar DESC,
            id_payment DESC
    """)

    with engine.connect() as conn:
        return conn.execute(
            sql,
            {
                "id_invoice": id_invoice
            }
        ).mappings().all()


# ==================================================
# DETAIL PAYMENT
# ==================================================
def get_payment_by_id(id_payment: int):
    sql = text("""
        SELECT
            p.*,

            i.no_invoice,
            i.nilai_invoice,

            c.nama_client

        FROM payments p

        JOIN invoices i
            ON i.id_invoice = p.id_invoice

        JOIN client c
            ON c.id_client = i.id_client

        WHERE p.id_payment = :id_payment
          AND p.status = 1

        LIMIT 1
    """)

    with engine.connect() as conn:
        return conn.execute(
            sql,
            {
                "id_payment": id_payment
            }
        ).mappings().first()


# ==================================================
# CREATE PAYMENT
# ==================================================
def create_payment(
    id_invoice,
    tanggal_bayar,
    jumlah_bayar,
    metode_bayar,
    nomor_referensi,
    keterangan
):
    sql = text("""
        INSERT INTO payments
        (
            id_invoice,
            tanggal_bayar,
            jumlah_bayar,
            metode_bayar,
            nomor_referensi,
            keterangan
        )
        VALUES
        (
            :id_invoice,
            :tanggal_bayar,
            :jumlah_bayar,
            :metode_bayar,
            :nomor_referensi,
            :keterangan
        )

        RETURNING *
    """)

    with engine.begin() as conn:
        return conn.execute(
            sql,
            {
                "id_invoice": id_invoice,
                "tanggal_bayar": tanggal_bayar,
                "jumlah_bayar": jumlah_bayar,
                "metode_bayar": metode_bayar,
                "nomor_referensi": nomor_referensi,
                "keterangan": keterangan
            }
        ).mappings().first()


# ==================================================
# UPDATE PAYMENT
# ==================================================
def update_payment(
    id_payment,
    tanggal_bayar,
    jumlah_bayar,
    metode_bayar,
    nomor_referensi,
    keterangan
):
    sql = text("""
        UPDATE payments
        SET
            tanggal_bayar = :tanggal_bayar,
            jumlah_bayar = :jumlah_bayar,
            metode_bayar = :metode_bayar,
            nomor_referensi = :nomor_referensi,
            keterangan = :keterangan,
            updated_at = CURRENT_TIMESTAMP

        WHERE id_payment = :id_payment
          AND status = 1

        RETURNING *
    """)

    with engine.begin() as conn:
        return conn.execute(
            sql,
            {
                "id_payment": id_payment,
                "tanggal_bayar": tanggal_bayar,
                "jumlah_bayar": jumlah_bayar,
                "metode_bayar": metode_bayar,
                "nomor_referensi": nomor_referensi,
                "keterangan": keterangan
            }
        ).mappings().first()


# ==================================================
# DELETE PAYMENT
# ==================================================
def delete_payment(id_payment: int):
    sql = text("""
        UPDATE payments
        SET
            status = 0,
            updated_at = CURRENT_TIMESTAMP

        WHERE id_payment = :id_payment
          AND status = 1

        RETURNING id_payment
    """)

    with engine.begin() as conn:
        return conn.execute(
            sql,
            {
                "id_payment": id_payment
            }
        ).mappings().first()