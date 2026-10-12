from sqlalchemy import text

from api.utils.config import engine


# ============================================================================ #
#                    #SECTION - DASHBOARD OVERVIEW                            #
# ============================================================================ #

def get_dashboard_overview():

    sql = """
        SELECT
            COUNT(*) AS total_work,

            COUNT(*) FILTER (
                WHERE wi.current_stage = 'CLOSED'
            ) AS completed,

            COUNT(*) FILTER (
                WHERE
                    wi.current_stage <> 'CLOSED'
                    AND wi.target_end_date < CURRENT_DATE
            ) AS expired,

            COUNT(*) FILTER (
                WHERE
                    wi.current_stage <> 'CLOSED'
                    AND wi.target_end_date >= CURRENT_DATE
                    AND (
                        wi.target_end_date - CURRENT_DATE
                    ) <= 30
            ) AS due_soon,

            COUNT(*) FILTER (
                WHERE
                    wi.current_stage <> 'CLOSED'
                    AND (
                        wi.target_end_date > CURRENT_DATE + 30
                        OR wi.target_end_date IS NULL
                    )
            ) AS on_track

        FROM work_items wi

        WHERE
            wi.is_active = 1
    """

    with engine.connect() as conn:
        return conn.execute(
            text(sql)
        ).mappings().first()


# ============================================================================ #
#                    #SECTION - DASHBOARD WORK TYPE                           #
# ============================================================================ #

def get_dashboard_work_type():

    sql = """
        SELECT
            COUNT(*) FILTER (
                WHERE wi.work_type = 'TENDER'
            ) AS tender,

            COUNT(*) FILTER (
                WHERE wi.work_type = 'MAINTENANCE'
            ) AS maintenance

        FROM work_items wi

        WHERE
            wi.is_active = 1
            AND wi.current_stage <> 'CLOSED'
    """

    with engine.connect() as conn:
        return conn.execute(
            text(sql)
        ).mappings().first()


# ============================================================================ #
#                    #SECTION - DASHBOARD PIPELINE                            #
# ============================================================================ #

def get_dashboard_pipeline():

    sql = """
        SELECT
            COUNT(*) FILTER (
                WHERE wi.current_stage = 'IDENTIFIED'
            ) AS identified,

            COUNT(*) FILTER (
                WHERE wi.current_stage = 'QUOTATION'
            ) AS quotation,

            COUNT(*) FILTER (
                WHERE wi.current_stage = 'CONTRACT'
            ) AS contract,

            COUNT(*) FILTER (
                WHERE wi.current_stage = 'BA'
            ) AS ba,

            COUNT(*) FILTER (
                WHERE wi.current_stage = 'INVOICE'
            ) AS invoice,

            COUNT(*) FILTER (
                WHERE wi.current_stage = 'PAYMENT'
            ) AS payment,

            COUNT(*) FILTER (
                WHERE wi.current_stage = 'CLOSED'
            ) AS closed

        FROM work_items wi

        WHERE
            wi.is_active = 1
    """

    with engine.connect() as conn:
        return conn.execute(
            text(sql)
        ).mappings().first()


# ============================================================================ #
#                    #SECTION - DASHBOARD FINANCIAL                           #
# ============================================================================ #

def get_dashboard_financial():

    sql = """
        WITH contract_summary AS (
            SELECT
                COALESCE(
                    SUM(
                        wc.contract_value
                        + (
                            wc.contract_value
                            * COALESCE(wc.vat_rate, 0)
                            / 100
                        )
                    ),
                    0
                ) AS contract_value

            FROM work_contracts wc

            INNER JOIN work_items wi
                ON wi.id_work_item = wc.id_work_item
                AND wi.is_active = 1
                AND wi.current_stage <> 'CLOSED'

            WHERE
                wc.is_active = 1
                AND wc.status <> 'CANCELLED'
        ),

        invoice_summary AS (
            SELECT
                COALESCE(
                    SUM(
                        winv.invoice_value
                        + (
                            winv.invoice_value
                            * COALESCE(winv.vat_rate, 0)
                            / 100
                        )
                    ),
                    0
                ) AS invoiced

            FROM work_invoices winv

            INNER JOIN work_items wi
                ON wi.id_work_item = winv.id_work_item
                AND wi.is_active = 1
                AND wi.current_stage <> 'CLOSED'

            WHERE
                winv.is_active = 1
        ),

        payment_summary AS (
            SELECT
                COALESCE(
                    SUM(wp.amount),
                    0
                ) AS paid

            FROM work_payments wp

            INNER JOIN work_invoices winv
                ON winv.id_invoice = wp.id_invoice
                AND winv.is_active = 1

            INNER JOIN work_items wi
                ON wi.id_work_item = winv.id_work_item
                AND wi.is_active = 1
                AND wi.current_stage <> 'CLOSED'

            WHERE
                wp.is_active = 1
        )

        SELECT
            cs.contract_value,
            ins.invoiced,
            ps.paid,

            GREATEST(
                ins.invoiced - ps.paid,
                0
            ) AS outstanding

        FROM contract_summary cs
        CROSS JOIN invoice_summary ins
        CROSS JOIN payment_summary ps
    """

    with engine.connect() as conn:
        return conn.execute(
            text(sql)
        ).mappings().first()


# ============================================================================ #
#                    #SECTION - DASHBOARD ATTENTION                           #
# ============================================================================ #

def get_dashboard_attention():

    sql = """
        WITH invoice_payment AS (
            SELECT
                winv.id_invoice,

                (
                    winv.invoice_value
                    + (
                        winv.invoice_value
                        * COALESCE(winv.vat_rate, 0)
                        / 100
                    )
                ) AS total_invoice,

                COALESCE(
                    SUM(
                        CASE
                            WHEN wp.is_active = 1
                                THEN wp.amount
                            ELSE 0
                        END
                    ),
                    0
                ) AS total_paid,

                winv.due_date

            FROM work_invoices winv

            INNER JOIN work_items wi
                ON wi.id_work_item = winv.id_work_item
                AND wi.is_active = 1
                AND wi.current_stage <> 'CLOSED'

            LEFT JOIN work_payments wp
                ON wp.id_invoice = winv.id_invoice

            WHERE
                winv.is_active = 1

            GROUP BY
                winv.id_invoice,
                winv.invoice_value,
                winv.vat_rate,
                winv.due_date
        )

        SELECT

            (
                SELECT COUNT(*)

                FROM work_items wi

                WHERE
                    wi.is_active = 1
                    AND wi.current_stage <> 'CLOSED'
                    AND wi.target_end_date < CURRENT_DATE

            ) AS expired_work,

            (
                SELECT COUNT(*)

                FROM work_items wi

                WHERE
                    wi.is_active = 1
                    AND wi.current_stage <> 'CLOSED'
                    AND wi.target_end_date >= CURRENT_DATE
                    AND (
                        wi.target_end_date - CURRENT_DATE
                    ) <= 30

            ) AS due_soon_work,

            (
                SELECT COUNT(*)

                FROM invoice_payment ip

                WHERE
                    ip.due_date < CURRENT_DATE
                    AND ip.total_paid < ip.total_invoice

            ) AS overdue_invoice,

            (
                SELECT COUNT(*)

                FROM invoice_payment ip

                WHERE
                    ip.total_paid = 0
                    AND ip.total_invoice > 0

            ) AS unpaid_invoice
    """

    with engine.connect() as conn:
        return conn.execute(
            text(sql)
        ).mappings().first()


# ============================================================================ #
#                    #SECTION - DASHBOARD ACTIVITY                            #
# ============================================================================ #

def get_dashboard_activity(limit: int = 10):

    sql = """
        WITH activities AS (

            -- ================================================================
            -- STAGE CHANGE
            -- ================================================================

            SELECT
                wsh.id_stage_history AS activity_id,
                'STAGE_CHANGE' AS activity_type,
                wi.work_number,
                wi.work_name,
                wsh.created_at AS activity_date,

                CONCAT(
                    'Stage pekerjaan berubah menjadi ',
                    wsh.stage
                ) AS title,

                CONCAT(
                    'Pekerjaan ',
                    wi.work_number,
                    ' berada pada stage ',
                    wsh.stage
                ) AS description

            FROM work_stage_histories wsh

            INNER JOIN work_items wi
                ON wi.id_work_item = wsh.id_work_item
                AND wi.is_active = 1

            WHERE
                wsh.is_active = 1


            UNION ALL


            -- ================================================================
            -- PROPOSAL
            -- ================================================================

            SELECT
                wp.id_proposal AS activity_id,
                'PROPOSAL' AS activity_type,
                wi.work_number,
                wi.work_name,
                wp.created_at AS activity_date,

                CONCAT(
                    'Penawaran ',
                    COALESCE(wp.proposal_number, '-'),
                    ' dibuat'
                ) AS title,

                CONCAT(
                    'Penawaran ',
                    COALESCE(wp.proposal_number, '-'),
                    ' dengan status ',
                    COALESCE(wp.status, '-')
                ) AS description

            FROM work_proposals wp

            INNER JOIN work_items wi
                ON wi.id_work_item = wp.id_work_item
                AND wi.is_active = 1

            WHERE
                wp.is_active = 1


            UNION ALL


            -- ================================================================
            -- CONTRACT
            -- ================================================================

            SELECT
                wc.id_contract AS activity_id,
                'CONTRACT' AS activity_type,
                wi.work_number,
                wi.work_name,
                wc.created_at AS activity_date,

                CONCAT(
                    'Kontrak ',
                    COALESCE(wc.contract_number, '-'),
                    ' dibuat'
                ) AS title,

                CONCAT(
                    'Kontrak ',
                    COALESCE(wc.contract_number, '-'),
                    ' dengan status ',
                    COALESCE(wc.status, '-')
                ) AS description

            FROM work_contracts wc

            INNER JOIN work_items wi
                ON wi.id_work_item = wc.id_work_item
                AND wi.is_active = 1

            WHERE
                wc.is_active = 1


            UNION ALL


            -- ================================================================
            -- BERITA ACARA
            -- ================================================================

            SELECT
                wcomp.id_completion AS activity_id,
                'BA' AS activity_type,
                wi.work_number,
                wi.work_name,
                wcomp.created_at AS activity_date,

                CONCAT(
                    'BA ',
                    COALESCE(wcomp.ba_number, '-'),
                    ' dibuat'
                ) AS title,

                CONCAT(
                    'Berita Acara ',
                    COALESCE(wcomp.ba_number, '-'),
                    ' telah dibuat'
                ) AS description

            FROM work_completions wcomp

            INNER JOIN work_items wi
                ON wi.id_work_item = wcomp.id_work_item
                AND wi.is_active = 1

            WHERE
                wcomp.is_active = 1


            UNION ALL


            -- ================================================================
            -- INVOICE
            -- ================================================================

            SELECT
                winv.id_invoice AS activity_id,
                'INVOICE' AS activity_type,
                wi.work_number,
                wi.work_name,
                winv.created_at AS activity_date,

                CONCAT(
                    'Invoice ',
                    COALESCE(winv.invoice_number, '-'),
                    ' dibuat'
                ) AS title,

                CONCAT(
                    'Invoice ',
                    COALESCE(winv.invoice_number, '-'),
                    ' telah dibuat'
                ) AS description

            FROM work_invoices winv

            INNER JOIN work_items wi
                ON wi.id_work_item = winv.id_work_item
                AND wi.is_active = 1

            WHERE
                winv.is_active = 1


            UNION ALL


            -- ================================================================
            -- PAYMENT
            -- ================================================================

            SELECT
                wp.id_payment AS activity_id,
                'PAYMENT' AS activity_type,
                wi.work_number,
                wi.work_name,
                wp.created_at AS activity_date,

                'Pembayaran diterima' AS title,

                CONCAT(
                    'Pembayaran sebesar Rp ',
                    TO_CHAR(
                        wp.amount,
                        'FM999G999G999G999G990D00'
                    ),
                    ' diterima'
                ) AS description

            FROM work_payments wp

            INNER JOIN work_invoices winv
                ON winv.id_invoice = wp.id_invoice
                AND winv.is_active = 1

            INNER JOIN work_items wi
                ON wi.id_work_item = winv.id_work_item
                AND wi.is_active = 1

            WHERE
                wp.is_active = 1
        )

        SELECT
            activity_id,
            activity_type,
            work_number,
            work_name,
            activity_date,
            title,
            description

        FROM activities

        ORDER BY
            activity_date DESC NULLS LAST

        LIMIT :limit
    """

    with engine.connect() as conn:
        return conn.execute(
            text(sql),
            {
                "limit": limit
            }
        ).mappings().all()