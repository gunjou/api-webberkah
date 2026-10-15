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


# ============================================================================ #
#                    #SECTION - DASHBOARD WORK SUMMARY                        #
# ============================================================================ #

def get_dashboard_work_summary():

    sql = """
        WITH work_data AS (
            SELECT
                wi.id_work_item,
                wi.work_number,
                wi.work_name,
                wi.work_type,

                wi.id_client,
                c.name AS client_name,

                wi.id_client_pic,
                cp.name AS client_pic_name,

                wi.internal_pic_name,

                -- =========================================================
                -- DERIVED STAGE
                -- CONTRACT + PROGRESS >= 100% = COMPLETED
                -- =========================================================

                CASE
                    WHEN wi.current_stage = 'CONTRACT'
                        AND wi.progress_percent >= 100
                        THEN 'COMPLETED'
                    ELSE wi.current_stage
                END AS current_stage,

                wi.progress_percent,
                wi.start_date,
                wi.target_end_date,
                wi.completion_date,

                -- =========================================================
                -- PROPOSAL
                -- =========================================================

                proposal.id_proposal,
                proposal.proposal_number,
                proposal.proposal_date,
                proposal.valid_until,

                -- =========================================================
                -- CONTRACT
                -- =========================================================

                contract.id_contract,
                contract.contract_number,
                contract.contract_date,
                contract.contract_start_date,
                contract.contract_end_date,

                -- =========================================================
                -- INVOICE
                -- =========================================================

                invoice.id_invoice,
                invoice.invoice_number,
                invoice.invoice_date,
                invoice.invoice_due_date,

                -- =========================================================
                -- WORK ITEM TIMESTAMP
                -- =========================================================

                wi.created_at,
                wi.updated_at

            FROM work_items wi

            LEFT JOIN client c
                ON c.id_client = wi.id_client

            LEFT JOIN client_pic cp
                ON cp.id_client_pic = wi.id_client_pic

            -- =============================================================
            -- PROPOSAL
            -- =============================================================

            LEFT JOIN LATERAL (
                SELECT
                    wp.id_proposal,
                    wp.proposal_number,
                    wp.proposal_date,
                    wp.valid_until
                FROM work_proposals wp
                WHERE
                    wp.id_work_item = wi.id_work_item
                    AND wp.is_active = 1
                ORDER BY
                    wp.proposal_date DESC NULLS LAST,
                    wp.created_at DESC
                LIMIT 1
            ) proposal
                ON TRUE

            -- =============================================================
            -- CONTRACT
            -- =============================================================

            LEFT JOIN LATERAL (
                SELECT
                    wc.id_contract,
                    wc.contract_number,
                    wc.contract_date,
                    wc.start_date AS contract_start_date,
                    wc.end_date AS contract_end_date
                FROM work_contracts wc
                WHERE
                    wc.id_work_item = wi.id_work_item
                    AND wc.is_active = 1
                    AND wc.status <> 'CANCELLED'
                ORDER BY
                    wc.contract_date DESC NULLS LAST,
                    wc.created_at DESC
                LIMIT 1
            ) contract
                ON TRUE

            -- =============================================================
            -- INVOICE
            -- =============================================================

            LEFT JOIN LATERAL (
                SELECT
                    inv.id_invoice,
                    inv.invoice_number,
                    inv.invoice_date,
                    inv.due_date AS invoice_due_date
                FROM work_invoices inv
                WHERE
                    inv.id_work_item = wi.id_work_item
                    AND inv.is_active = 1
                ORDER BY
                    inv.invoice_date DESC NULLS LAST,
                    inv.created_at DESC
                LIMIT 1
            ) invoice
                ON TRUE

            WHERE
                wi.is_active = 1
                AND wi.current_stage <> 'CLOSED'
        ),

        deadline_data AS (
            SELECT
                wd.*,

                -- =========================================================
                -- DEADLINE BERDASARKAN CURRENT STAGE
                -- =========================================================

                CASE
                    WHEN wd.current_stage = 'IDENTIFIED'
                        THEN wd.completion_date

                    WHEN wd.current_stage = 'QUOTATION'
                        THEN wd.valid_until

                    WHEN wd.current_stage = 'CONTRACT'
                        THEN wd.contract_end_date

                    WHEN wd.current_stage = 'COMPLETED'
                        THEN wd.contract_end_date

                    WHEN wd.current_stage = 'BA'
                        THEN wd.contract_end_date

                    WHEN wd.current_stage = 'INVOICE'
                        THEN wd.invoice_due_date

                    WHEN wd.current_stage = 'PAYMENT'
                        THEN wd.invoice_due_date

                    ELSE NULL
                END AS deadline_date

            FROM work_data wd
        )

        SELECT
            id_work_item,
            work_number,
            work_name,
            work_type,

            id_client,
            client_name,

            id_client_pic,
            client_pic_name,

            internal_pic_name,

            current_stage,
            progress_percent,

            start_date,
            target_end_date,
            completion_date,

            id_proposal,
            proposal_number,
            proposal_date,
            valid_until,

            id_contract,
            contract_number,
            contract_date,
            contract_start_date,
            contract_end_date,

            id_invoice,
            invoice_number,
            invoice_date,
            invoice_due_date,

            -- =============================================================
            -- DEADLINE AKTUAL
            -- =============================================================

            deadline_date,

            -- =============================================================
            -- HEALTH
            -- =============================================================

            CASE
                WHEN deadline_date IS NULL
                    THEN NULL

                WHEN deadline_date < CURRENT_DATE
                    THEN 'EXPIRED'

                WHEN deadline_date <= CURRENT_DATE + 30
                    THEN 'DUE_SOON'

                ELSE 'ON_TRACK'
            END AS health_status,

            -- =============================================================
            -- SELISIH HARI
            -- =============================================================

            CASE
                WHEN deadline_date IS NULL
                    THEN NULL

                ELSE deadline_date - CURRENT_DATE
            END AS days_to_deadline,

            created_at,
            updated_at

        FROM deadline_data

        ORDER BY
            CASE
                WHEN current_stage = 'IDENTIFIED'
                    THEN 1

                WHEN current_stage = 'QUOTATION'
                    THEN 2

                WHEN current_stage = 'CONTRACT'
                    THEN 3

                WHEN current_stage = 'COMPLETED'
                    THEN 4

                WHEN current_stage = 'BA'
                    THEN 5

                WHEN current_stage = 'INVOICE'
                    THEN 6

                WHEN current_stage = 'PAYMENT'
                    THEN 7

                ELSE 8
            END,

            deadline_date ASC NULLS LAST,
            created_at DESC
    """

    with engine.connect() as conn:
        return conn.execute(
            text(sql)
        ).mappings().all()


# ============================================================================ #
#                    #SECTION - DASHBOARD WORK WARNINGS                       #
# ============================================================================ #

def get_dashboard_warnings():

    sql = """
        WITH work_data AS (
            SELECT
                wi.id_work_item,
                wi.work_number,
                wi.work_name,
                wi.work_type,

                wi.id_client,
                c.name AS client_name,

                wi.id_client_pic,
                cp.name AS client_pic_name,

                wi.internal_pic_name,

                CASE
                    WHEN wi.current_stage = 'CONTRACT'
                        AND wi.progress_percent >= 100
                        THEN 'COMPLETED'
                    ELSE wi.current_stage
                END AS current_stage,

                wi.progress_percent,
                wi.start_date,
                wi.completion_date,

                proposal.proposal_number,
                proposal.proposal_date,
                proposal.valid_until,

                contract.contract_number,
                contract.contract_date,
                contract.start_date AS contract_start_date,
                contract.end_date AS contract_end_date,

                invoice.id_invoice,
                invoice.invoice_number,
                invoice.invoice_date,
                invoice.due_date AS invoice_due_date,
                invoice.total_invoice,
                invoice.paid_amount,
                invoice.outstanding_amount

            FROM work_items wi

            LEFT JOIN client c
                ON c.id_client = wi.id_client

            LEFT JOIN client_pic cp
                ON cp.id_client_pic = wi.id_client_pic

            -- =============================================================
            -- PROPOSAL
            -- =============================================================

            LEFT JOIN LATERAL (
                SELECT
                    wp.proposal_number,
                    wp.proposal_date,
                    wp.valid_until
                FROM work_proposals wp
                WHERE
                    wp.id_work_item = wi.id_work_item
                    AND wp.is_active = 1
                ORDER BY
                    wp.proposal_date DESC NULLS LAST,
                    wp.created_at DESC
                LIMIT 1
            ) proposal
                ON TRUE

            -- =============================================================
            -- CONTRACT
            -- =============================================================

            LEFT JOIN LATERAL (
                SELECT
                    wc.contract_number,
                    wc.contract_date,
                    wc.start_date,
                    wc.end_date
                FROM work_contracts wc
                WHERE
                    wc.id_work_item = wi.id_work_item
                    AND wc.is_active = 1
                    AND wc.status <> 'CANCELLED'
                ORDER BY
                    wc.contract_date DESC NULLS LAST,
                    wc.created_at DESC
                LIMIT 1
            ) contract
                ON TRUE

            -- =============================================================
            -- INVOICE + PAYMENT
            -- =============================================================

            LEFT JOIN LATERAL (
                SELECT
                    inv.id_invoice,
                    inv.invoice_number,
                    inv.invoice_date,
                    inv.due_date,

                    (
                        inv.invoice_value
                        + (
                            inv.invoice_value
                            * COALESCE(inv.vat_rate, 0) / 100.0
                        )
                    ) AS total_invoice,

                    COALESCE(
                        (
                            SELECT SUM(p.amount)
                            FROM work_payments p
                            WHERE
                                p.id_invoice = inv.id_invoice
                                AND p.is_active = 1
                        ),
                        0
                    ) AS paid_amount,

                    GREATEST(
                        (
                            inv.invoice_value
                            + (
                                inv.invoice_value
                                * COALESCE(inv.vat_rate, 0) / 100.0
                            )
                        )
                        -
                        COALESCE(
                            (
                                SELECT SUM(p.amount)
                                FROM work_payments p
                                WHERE
                                    p.id_invoice = inv.id_invoice
                                    AND p.is_active = 1
                            ),
                            0
                        ),
                        0
                    ) AS outstanding_amount

                FROM work_invoices inv

                WHERE
                    inv.id_work_item = wi.id_work_item
                    AND inv.is_active = 1

                ORDER BY
                    inv.invoice_date DESC NULLS LAST,
                    inv.created_at DESC

                LIMIT 1
            ) invoice
                ON TRUE

            WHERE
                wi.is_active = 1
                AND wi.current_stage <> 'CLOSED'
        ),

        deadline_data AS (
            SELECT
                wd.*,

                CASE
                    -- =====================================================
                    -- IDENTIFIED
                    -- =====================================================

                    WHEN wd.current_stage = 'IDENTIFIED'
                        THEN wd.completion_date

                    -- =====================================================
                    -- QUOTATION
                    -- =====================================================

                    WHEN wd.current_stage = 'QUOTATION'
                        THEN wd.valid_until

                    -- =====================================================
                    -- CONTRACT
                    -- =====================================================

                    WHEN wd.current_stage = 'CONTRACT'
                        THEN wd.contract_end_date

                    -- =====================================================
                    -- COMPLETED
                    -- =====================================================

                    WHEN wd.current_stage = 'COMPLETED'
                        THEN wd.contract_end_date

                    -- =====================================================
                    -- BA
                    -- =====================================================

                    WHEN wd.current_stage = 'BA'
                        THEN wd.contract_end_date

                    -- =====================================================
                    -- INVOICE
                    -- =====================================================

                    WHEN wd.current_stage = 'INVOICE'
                        THEN wd.invoice_due_date

                    -- =====================================================
                    -- PAYMENT
                    -- =====================================================

                    WHEN wd.current_stage = 'PAYMENT'
                        THEN wd.invoice_due_date

                    ELSE NULL
                END AS deadline_date

            FROM work_data wd
        ),

        warning_data AS (
            SELECT
                dd.*,

                CASE
                    WHEN dd.deadline_date < CURRENT_DATE
                        THEN 'EXPIRED'

                    WHEN dd.deadline_date <= CURRENT_DATE + 30
                        THEN 'DUE_SOON'

                    ELSE 'ON_TRACK'
                END AS health_status,

                CASE
                    WHEN dd.deadline_date IS NULL
                        THEN NULL

                    ELSE dd.deadline_date - CURRENT_DATE
                END AS days_to_deadline

            FROM deadline_data dd

            WHERE
                dd.deadline_date IS NOT NULL
        )

        SELECT
            id_work_item,
            work_number,
            work_name,
            work_type,

            id_client,
            client_name,

            id_client_pic,
            client_pic_name,

            internal_pic_name,

            current_stage,
            progress_percent,

            start_date,
            completion_date,

            proposal_number,
            proposal_date,
            valid_until,

            contract_number,
            contract_date,
            contract_start_date,
            contract_end_date,

            id_invoice,
            invoice_number,
            invoice_date,
            invoice_due_date,

            total_invoice,
            paid_amount,
            outstanding_amount,

            deadline_date,
            health_status,
            days_to_deadline,

            CASE
                WHEN current_stage IN (
                    'IDENTIFIED',
                    'QUOTATION',
                    'CONTRACT',
                    'COMPLETED',
                    'BA'
                )
                    THEN 'WORK'

                WHEN current_stage = 'INVOICE'
                    THEN 'INVOICE'

                WHEN current_stage = 'PAYMENT'
                    THEN 'PAYMENT'

                ELSE 'WORK'
            END AS warning_type

        FROM warning_data

        WHERE
            health_status IN (
                'EXPIRED',
                'DUE_SOON'
            )

            -- =============================================================
            -- PAYMENT hanya warning jika masih ada outstanding
            -- =============================================================

            AND (
                current_stage <> 'PAYMENT'
                OR outstanding_amount > 0
            )

        ORDER BY
            CASE
                WHEN health_status = 'EXPIRED'
                    THEN 1

                WHEN health_status = 'DUE_SOON'
                    THEN 2

                ELSE 3
            END,

            deadline_date ASC,
            work_number ASC
    """

    with engine.connect() as conn:
        return conn.execute(
            text(sql)
        ).mappings().all()


# ============================================================================ #
#                    #SECTION - CONTRACT FINANCIALS                            #
# ============================================================================ #

def get_dashboard_contract_financials():

    sql = """
        SELECT
            wc.id_contract,
            wc.id_work_item,
            wc.contract_number,
            wc.contract_date,
            wc.contract_value,
            COALESCE(wc.vat_rate, 0) AS vat_rate,

            ROUND(
                wc.contract_value
                * (1 + COALESCE(wc.vat_rate, 0) / 100.0),
                2
            ) AS total_contract_value,

            wi.work_number,
            wi.work_name,
            wi.work_type,
            wi.current_stage,

            c.name AS client_name

        FROM work_contracts wc

        INNER JOIN work_items wi
            ON wi.id_work_item = wc.id_work_item

        LEFT JOIN client c
            ON c.id_client = wi.id_client

        WHERE
            wc.is_active = 1
            AND wc.status = 'ACTIVE'
            AND wi.is_active = 1
            AND wi.current_stage <> 'CLOSED'

        ORDER BY
            wc.contract_date DESC NULLS LAST,
            wc.created_at DESC
    """

    with engine.connect() as conn:
        return conn.execute(text(sql)).mappings().all()


# ============================================================================ #
#                    #SECTION - UNBILLED FINANCIALS                            #
# ============================================================================ #

def get_dashboard_unbilled_financials():

    sql = """
        WITH contract_summary AS (
            SELECT
                wc.id_work_item,

                SUM(
                    ROUND(
                        wc.contract_value
                        * (1 + COALESCE(wc.vat_rate, 0) / 100.0),
                        2
                    )
                ) AS total_contract_value

            FROM work_contracts wc

            WHERE
                wc.is_active = 1
                AND wc.status = 'ACTIVE'

            GROUP BY wc.id_work_item
        )

        SELECT
            wi.id_work_item,
            wi.work_number,
            wi.work_name,
            wi.work_type,
            wi.current_stage,

            c.name AS client_name,

            ba.id_completion,
            ba.ba_number,
            ba.ba_date,

            COALESCE(
                cs.total_contract_value,
                0
            ) AS total_contract_value

        FROM work_items wi

        INNER JOIN work_completions ba
            ON ba.id_work_item = wi.id_work_item
            AND ba.is_active = 1

        LEFT JOIN contract_summary cs
            ON cs.id_work_item = wi.id_work_item

        LEFT JOIN client c
            ON c.id_client = wi.id_client

        WHERE
            wi.is_active = 1
            AND wi.current_stage = 'BA'

            AND NOT EXISTS (
                SELECT 1
                FROM work_invoices inv
                WHERE
                    inv.id_work_item = wi.id_work_item
                    AND inv.is_active = 1
            )

        ORDER BY
            ba.ba_date ASC NULLS LAST,
            wi.work_number ASC
    """

    with engine.connect() as conn:
        return conn.execute(text(sql)).mappings().all()


# ============================================================================ #
#                    #SECTION - UNPAID INVOICE FINANCIALS                      #
# ============================================================================ #

def get_dashboard_unpaid_invoice_financials():

    sql = """
        WITH payment_summary AS (
            SELECT
                p.id_invoice,
                SUM(p.amount) AS paid_amount

            FROM work_payments p

            WHERE p.is_active = 1

            GROUP BY p.id_invoice
        ),

        invoice_summary AS (
            SELECT
                inv.id_invoice,
                inv.id_work_item,
                inv.invoice_number,
                inv.invoice_date,
                inv.due_date,
                inv.invoice_value,
                COALESCE(inv.vat_rate, 0) AS vat_rate,

                ROUND(
                    inv.invoice_value
                    * (
                        1 + COALESCE(inv.vat_rate, 0) / 100.0
                    ),
                    2
                ) AS total_invoice,

                COALESCE(ps.paid_amount, 0) AS paid_amount,

                wi.work_number,
                wi.work_name,
                wi.work_type,
                wi.current_stage,

                c.name AS client_name

            FROM work_invoices inv

            INNER JOIN work_items wi
                ON wi.id_work_item = inv.id_work_item

            LEFT JOIN client c
                ON c.id_client = wi.id_client
            LEFT JOIN payment_summary ps
                ON ps.id_invoice = inv.id_invoice
            WHERE
                inv.is_active = 1
                AND wi.is_active = 1
                AND wi.current_stage NOT IN ('PAYMENT', 'CLOSED')
        )
        SELECT
            id_invoice,
            id_work_item,
            invoice_number,
            invoice_date,
            due_date,
            invoice_value,
            vat_rate,
            total_invoice,
            paid_amount,
            GREATEST(
                total_invoice - paid_amount,
                0
            ) AS outstanding_amount,
            work_number,
            work_name,
            work_type,
            current_stage,
            client_name
        FROM invoice_summary
        WHERE total_invoice - paid_amount > 0
        ORDER BY
            due_date ASC NULLS LAST,
            invoice_date ASC NULLS LAST,
            invoice_number ASC
    """

    with engine.connect() as conn:
        return conn.execute(text(sql)).mappings().all()


# ============================================================================ #
#                    #SECTION - PAID INVOICE FINANCIALS                        #
# ============================================================================ #

def get_dashboard_paid_invoice_financials():

    sql = """
        WITH payment_summary AS (
            SELECT
                p.id_invoice,
                SUM(p.amount) AS paid_amount
            FROM work_payments p
            WHERE p.is_active = 1
            GROUP BY p.id_invoice
        )
        SELECT
            inv.id_invoice,
            inv.id_work_item,
            inv.invoice_number,
            inv.invoice_date,
            inv.due_date,
            inv.invoice_value,
            COALESCE(inv.vat_rate, 0) AS vat_rate,
            ROUND(
                inv.invoice_value
                * (
                    1 + COALESCE(inv.vat_rate, 0) / 100.0
                ),
                2
            ) AS total_invoice,
            COALESCE(
                ps.paid_amount,
                0
            ) AS total_received,
            wi.work_number,
            wi.work_name,
            wi.work_type,
            wi.current_stage,
            c.name AS client_name
        FROM work_invoices inv
        INNER JOIN work_items wi
            ON wi.id_work_item = inv.id_work_item
        LEFT JOIN client c
            ON c.id_client = wi.id_client
        LEFT JOIN payment_summary ps
            ON ps.id_invoice = inv.id_invoice
        WHERE
            inv.is_active = 1
            AND wi.is_active = 1
            AND wi.current_stage = 'PAYMENT'
        ORDER BY
            inv.invoice_date DESC NULLS LAST,
            inv.invoice_number ASC
    """

    with engine.connect() as conn:
        return conn.execute(text(sql)).mappings().all()