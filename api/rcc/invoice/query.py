from sqlalchemy import text
from api.utils.config import engine


# ==================================================
# LIST INVOICE
# ==================================================
def get_invoice_list(
    client=None,
    payment_status=None,
    health_status=None,
    start_date=None,
    end_date=None
):
    sql = text("""
        WITH payment_summary AS (
            SELECT
                p.id_invoice,
                COALESCE(
                    SUM(p.jumlah_bayar),
                    0
                ) AS total_bayar
            FROM payments p
            WHERE p.status = 1
            GROUP BY p.id_invoice
        )

        SELECT
            i.id_invoice,
            i.no_invoice,
            i.tanggal_invoice,
            i.tanggal_jatuh_tempo,
            i.nilai_invoice,
            i.keterangan,

            c.id_client,
            c.nama_client,

            COALESCE(
                ps.total_bayar,
                0
            ) AS total_bayar,

            (
                i.nilai_invoice -
                COALESCE(
                    ps.total_bayar,
                    0
                )
            ) AS sisa_tagihan,

            GREATEST(
                CURRENT_DATE - i.tanggal_jatuh_tempo,
                0
            ) AS overdue_days,

            CASE
                WHEN COALESCE(
                    ps.total_bayar,
                    0
                ) = 0
                THEN 'BELUM_DIBAYAR'

                WHEN COALESCE(
                    ps.total_bayar,
                    0
                ) >= i.nilai_invoice
                THEN 'LUNAS'

                ELSE 'SEBAGIAN_DIBAYAR'
            END AS payment_status,

            CASE
                WHEN (
                    CURRENT_DATE -
                    i.tanggal_jatuh_tempo
                ) <= 30
                THEN 'NORMAL'

                WHEN (
                    CURRENT_DATE -
                    i.tanggal_jatuh_tempo
                ) <= 60
                THEN 'PERHATIAN'

                WHEN (
                    CURRENT_DATE -
                    i.tanggal_jatuh_tempo
                ) <= 89
                THEN 'TERLAMBAT'

                ELSE 'KRITIS'
            END AS health_status

        FROM invoices i

        JOIN client c
            ON c.id_client = i.id_client

        LEFT JOIN payment_summary ps
            ON ps.id_invoice = i.id_invoice

        WHERE i.status = 1

          AND (
                :client IS NULL
                OR i.id_client = :client
          )

          AND (
                :start_date IS NULL
                OR i.tanggal_invoice >= :start_date
          )

          AND (
                :end_date IS NULL
                OR i.tanggal_invoice <= :end_date
          )

        ORDER BY
            i.tanggal_invoice DESC,
            i.id_invoice DESC
    """)

    with engine.connect() as conn:
        rows = conn.execute(
            sql,
            {
                "client": client,
                "start_date": start_date,
                "end_date": end_date
            }
        ).mappings().all()

    result = []

    for row in rows:

        if (
            payment_status
            and row["payment_status"] != payment_status
        ):
            continue

        if (
            health_status
            and row["health_status"] != health_status
        ):
            continue

        result.append(dict(row))

    return result


# ==================================================
# DETAIL INVOICE
# ==================================================
def get_invoice_by_id(id_invoice: int):
    sql = text("""
        WITH payment_summary AS (
            SELECT
                p.id_invoice,
                COALESCE(
                    SUM(p.jumlah_bayar),
                    0
                ) AS total_bayar
            FROM payments p
            WHERE p.status = 1
            GROUP BY p.id_invoice
        )

        SELECT
            i.*,

            c.nama_client,

            COALESCE(
                ps.total_bayar,
                0
            ) AS total_bayar,

            (
                i.nilai_invoice -
                COALESCE(
                    ps.total_bayar,
                    0
                )
            ) AS sisa_tagihan

        FROM invoices i

        JOIN client c
            ON c.id_client = i.id_client

        LEFT JOIN payment_summary ps
            ON ps.id_invoice = i.id_invoice

        WHERE i.id_invoice = :id_invoice
          AND i.status = 1

        LIMIT 1
    """)

    with engine.connect() as conn:
        return conn.execute(
            sql,
            {
                "id_invoice": id_invoice
            }
        ).mappings().first()


# ==================================================
# PAYMENT HISTORY
# ==================================================
def get_invoice_payments(id_invoice: int):
    sql = text("""
        SELECT
            id_payment,
            tanggal_bayar,
            jumlah_bayar,
            metode_bayar,
            nomor_referensi,
            keterangan,
            created_at
        FROM payments
        WHERE id_invoice = :id_invoice
          AND status = 1
        ORDER BY tanggal_bayar DESC
    """)

    with engine.connect() as conn:
        return conn.execute(
            sql,
            {
                "id_invoice": id_invoice
            }
        ).mappings().all()


# ==================================================
# ATTACHMENT LIST
# ==================================================
def get_invoice_attachments(id_invoice: int):
    sql = text("""
        SELECT
            a.id_attachment,
            a.nama_file,
            a.path_file,
            a.mime_type,
            a.ukuran_file,
            a.keterangan,

            t.nama_type

        FROM attachments a

        LEFT JOIN ref_attachment_types t
            ON t.id_attachment_type =
               a.id_attachment_type

        WHERE a.id_invoice = :id_invoice
          AND a.status = 1

        ORDER BY a.id_attachment DESC
    """)

    with engine.connect() as conn:
        return conn.execute(
            sql,
            {
                "id_invoice": id_invoice
            }
        ).mappings().all()


# ==================================================
# CREATE INVOICE
# ==================================================
def create_invoice(
    id_client,
    no_invoice,
    tanggal_invoice,
    tanggal_jatuh_tempo,
    nilai_invoice,
    keterangan
):
    sql = text("""
        INSERT INTO invoices
        (
            id_client,
            no_invoice,
            tanggal_invoice,
            tanggal_jatuh_tempo,
            nilai_invoice,
            keterangan
        )
        VALUES
        (
            :id_client,
            :no_invoice,
            :tanggal_invoice,
            :tanggal_jatuh_tempo,
            :nilai_invoice,
            :keterangan
        )

        RETURNING *
    """)

    with engine.begin() as conn:
        return conn.execute(
            sql,
            {
                "id_client": id_client,
                "no_invoice": no_invoice,
                "tanggal_invoice": tanggal_invoice,
                "tanggal_jatuh_tempo": tanggal_jatuh_tempo,
                "nilai_invoice": nilai_invoice,
                "keterangan": keterangan
            }
        ).mappings().first()


# ==================================================
# UPDATE INVOICE
# ==================================================
def update_invoice(
    id_invoice,
    id_client,
    no_invoice,
    tanggal_invoice,
    tanggal_jatuh_tempo,
    nilai_invoice,
    keterangan
):
    sql = text("""
        UPDATE invoices
        SET
            id_client = :id_client,
            no_invoice = :no_invoice,
            tanggal_invoice = :tanggal_invoice,
            tanggal_jatuh_tempo = :tanggal_jatuh_tempo,
            nilai_invoice = :nilai_invoice,
            keterangan = :keterangan,
            updated_at = CURRENT_TIMESTAMP

        WHERE id_invoice = :id_invoice
          AND status = 1

        RETURNING *
    """)

    with engine.begin() as conn:
        return conn.execute(
            sql,
            {
                "id_invoice": id_invoice,
                "id_client": id_client,
                "no_invoice": no_invoice,
                "tanggal_invoice": tanggal_invoice,
                "tanggal_jatuh_tempo": tanggal_jatuh_tempo,
                "nilai_invoice": nilai_invoice,
                "keterangan": keterangan
            }
        ).mappings().first()


# ==================================================
# DELETE INVOICE
# ==================================================
def delete_invoice(id_invoice: int):
    sql = text("""
        UPDATE invoices
        SET
            status = 0,
            updated_at = CURRENT_TIMESTAMP

        WHERE id_invoice = :id_invoice
          AND status = 1

        RETURNING id_invoice
    """)

    with engine.begin() as conn:
        return conn.execute(
            sql,
            {
                "id_invoice": id_invoice
            }
        ).mappings().first()