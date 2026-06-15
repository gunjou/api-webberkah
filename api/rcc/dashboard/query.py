from sqlalchemy import text
from api.utils.config import engine


# ==================================================
# SUMMARY DASHBOARD
# ==================================================
def get_dashboard_summary():
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
            ) AS total_piutang,

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
            ON ps.id_invoice =
               i.id_invoice

        WHERE i.status = 1
    """)

    with engine.connect() as conn:
        return conn.execute(
            sql
        ).mappings().first()



# ==================================================
# INVOICE MONITORING
# ==================================================
def get_invoice_monitoring():
    sql = text("""
        WITH monitoring AS (
            SELECT

                CASE

                    WHEN (
                        CURRENT_DATE -
                        tanggal_jatuh_tempo
                    ) <= 30
                    THEN 'NORMAL'

                    WHEN (
                        CURRENT_DATE -
                        tanggal_jatuh_tempo
                    ) <= 60
                    THEN 'PERHATIAN'

                    WHEN (
                        CURRENT_DATE -
                        tanggal_jatuh_tempo
                    ) <= 89
                    THEN 'WASPADA'

                    ELSE 'KRITIS'

                END AS health_status

            FROM invoices

            WHERE status = 1
        )

        SELECT
            health_status,
            COUNT(*) AS total
        FROM monitoring
        GROUP BY health_status
        ORDER BY health_status
    """)

    with engine.connect() as conn:
        return conn.execute(
            sql
        ).mappings().all()



# ==================================================
# AGING INVOICE
# ==================================================
def get_aging_invoice():
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

                END AS aging_group

            FROM invoices

            WHERE status = 1
        )

        SELECT
            aging_group,
            COUNT(*) AS total
        FROM aging
        GROUP BY aging_group
        ORDER BY aging_group
    """)

    with engine.connect() as conn:
        return conn.execute(
            sql
        ).mappings().all()



# ==================================================
# TOP OUTSTANDING CLIENT
# ==================================================
def get_top_outstanding_client():
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
            ) AS total_piutang

        FROM client c

        JOIN invoices i
            ON i.id_client =
               c.id_client

        LEFT JOIN payment_summary ps
            ON ps.id_invoice =
               i.id_invoice

        WHERE c.status = 1
          AND i.status = 1

        GROUP BY
            c.id_client,
            c.nama_client

        ORDER BY
            total_piutang DESC

        LIMIT 10
    """)

    with engine.connect() as conn:
        return conn.execute(
            sql
        ).mappings().all()
