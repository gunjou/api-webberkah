from sqlalchemy import text
from api.utils.config import engine


# ==================================================
# EXECUTIVE SUMMARY
# ==================================================
def get_eis_summary():
    sql = text("""
        WITH payment_summary AS (
            SELECT
                id_invoice,
                COALESCE(
                    SUM(jumlah_bayar),
                    0
                ) AS total_bayar
            FROM payments
            WHERE status = 1
            GROUP BY id_invoice
        )

        SELECT

            COUNT(*) AS total_invoice,

            COALESCE(
                SUM(i.nilai_invoice),
                0
            ) AS total_nilai_invoice,

            COALESCE(
                SUM(
                    i.nilai_invoice -
                    COALESCE(
                        ps.total_bayar,
                        0
                    )
                ),
                0
            ) AS total_outstanding,

            COUNT(*) FILTER (
                WHERE COALESCE(
                    ps.total_bayar,
                    0
                ) = 0
            ) AS invoice_belum_dibayar,

            COUNT(*) FILTER (
                WHERE COALESCE(
                    ps.total_bayar,
                    0
                ) >= i.nilai_invoice
            ) AS invoice_lunas

        FROM invoices i

        LEFT JOIN payment_summary ps
            ON ps.id_invoice = i.id_invoice

        WHERE i.status = 1
    """)

    with engine.connect() as conn:
        return conn.execute(
            sql
        ).mappings().first()



# ==================================================
# CRITICAL INVOICE
# ==================================================
def get_critical_invoices():
    sql = text("""
        WITH payment_summary AS (
            SELECT
                id_invoice,
                COALESCE(
                    SUM(jumlah_bayar),
                    0
                ) AS total_bayar
            FROM payments
            WHERE status = 1
            GROUP BY id_invoice
        )

        SELECT

            i.id_invoice,
            i.no_invoice,

            c.nama_client,

            i.nilai_invoice,

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
            ) AS outstanding,

            (
                CURRENT_DATE -
                i.tanggal_jatuh_tempo
            ) AS overdue_days

        FROM invoices i

        JOIN client c
            ON c.id_client = i.id_client

        LEFT JOIN payment_summary ps
            ON ps.id_invoice = i.id_invoice

        WHERE i.status = 1

          AND (
                CURRENT_DATE -
                i.tanggal_jatuh_tempo
          ) >= 90

        ORDER BY
            overdue_days DESC,
            outstanding DESC
    """)

    with engine.connect() as conn:
        return conn.execute(
            sql
        ).mappings().all()



# ==================================================
# OUTSTANDING CLIENT
# ==================================================
def get_outstanding_clients():
    sql = text("""
        WITH payment_summary AS (
            SELECT
                id_invoice,
                COALESCE(
                    SUM(jumlah_bayar),
                    0
                ) AS total_bayar
            FROM payments
            WHERE status = 1
            GROUP BY id_invoice
        )

        SELECT

            c.id_client,
            c.nama_client,

            COALESCE(
                SUM(
                    i.nilai_invoice -
                    COALESCE(
                        ps.total_bayar,
                        0
                    )
                ),
                0
            ) AS total_outstanding

        FROM client c

        JOIN invoices i
            ON i.id_client = c.id_client

        LEFT JOIN payment_summary ps
            ON ps.id_invoice = i.id_invoice

        WHERE c.status = 1
          AND i.status = 1

        GROUP BY
            c.id_client,
            c.nama_client

        ORDER BY
            total_outstanding DESC

        LIMIT 10
    """)

    with engine.connect() as conn:
        return conn.execute(
            sql
        ).mappings().all()



# ==================================================
# AGING ANALYSIS
# ==================================================
def get_aging_analysis():
    sql = text("""
        WITH aging AS (

            SELECT

                CASE

                    WHEN (
                        CURRENT_DATE -
                        tanggal_jatuh_tempo
                    ) BETWEEN 0 AND 30
                    THEN '0-30'

                    WHEN (
                        CURRENT_DATE -
                        tanggal_jatuh_tempo
                    ) BETWEEN 31 AND 60
                    THEN '31-60'

                    WHEN (
                        CURRENT_DATE -
                        tanggal_jatuh_tempo
                    ) BETWEEN 61 AND 90
                    THEN '61-90'

                    ELSE '>90'

                END AS aging_group,

                nilai_invoice

            FROM invoices

            WHERE status = 1
        )

        SELECT

            aging_group,

            COUNT(*) AS total_invoice,

            COALESCE(
                SUM(nilai_invoice),
                0
            ) AS total_nilai

        FROM aging

        GROUP BY aging_group

        ORDER BY aging_group
    """)

    with engine.connect() as conn:
        return conn.execute(
            sql
        ).mappings().all()



# ==================================================
# INVOICE TREND
# ==================================================
def get_invoice_trend():
    sql = text("""
        WITH invoice_trend AS (

            SELECT

                TO_CHAR(
                    tanggal_invoice,
                    'YYYY-MM'
                ) AS periode,

                SUM(
                    nilai_invoice
                ) AS total_invoice

            FROM invoices

            WHERE status = 1

            GROUP BY periode
        ),

        payment_trend AS (

            SELECT

                TO_CHAR(
                    tanggal_bayar,
                    'YYYY-MM'
                ) AS periode,

                SUM(
                    jumlah_bayar
                ) AS total_payment

            FROM payments

            WHERE status = 1

            GROUP BY periode
        )

        SELECT

            COALESCE(
                i.periode,
                p.periode
            ) AS periode,

            COALESCE(
                i.total_invoice,
                0
            ) AS total_invoice,

            COALESCE(
                p.total_payment,
                0
            ) AS total_payment

        FROM invoice_trend i

        FULL OUTER JOIN payment_trend p
            ON p.periode = i.periode

        ORDER BY periode
    """)

    with engine.connect() as conn:
        return conn.execute(
            sql
        ).mappings().all()
