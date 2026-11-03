from sqlalchemy import text

from api.utils.config import engine


# ============================================================================ #
#                         #SECTION - SHARED SQL FRAGMENT                       #
# ============================================================================ #

# Tingkat reminder berdasarkan selisih hari ke deadline
def _reminder_level_sql(days_expr):
    return f"""
        CASE
            WHEN {days_expr} IS NULL THEN NULL
            WHEN {days_expr} < 0 THEN 'OVERDUE'
            WHEN {days_expr} = 0 THEN 'TODAY'
            WHEN {days_expr} <= 3 THEN 'H-3'
            WHEN {days_expr} <= 7 THEN 'H-7'
            WHEN {days_expr} <= 14 THEN 'H-14'
            WHEN {days_expr} <= 30 THEN 'H-30'
            ELSE 'ON_TRACK'
        END
    """


# Sisa tagihan per invoice (nilai + PPN - pembayaran)
INVOICE_OUTSTANDING_CTE = """
    payment_summary AS (
        SELECT
            p.id_invoice,
            SUM(p.amount) AS paid_amount
        FROM work_payments p
        WHERE p.is_active = 1
        GROUP BY p.id_invoice
    ),

    invoice_outstanding AS (
        SELECT
            inv.id_invoice,
            inv.id_work_item,
            inv.invoice_number,
            inv.invoice_date,
            inv.due_date,

            ROUND(
                COALESCE(inv.invoice_value, 0)
                * (1 + COALESCE(inv.vat_rate, 0) / 100.0),
                2
            ) AS total_invoice,

            COALESCE(ps.paid_amount, 0) AS paid_amount

        FROM work_invoices inv

        LEFT JOIN payment_summary ps
            ON ps.id_invoice = inv.id_invoice

        WHERE inv.is_active = 1
    ),

    invoice_unpaid AS (
        SELECT
            io.*,
            GREATEST(io.total_invoice - io.paid_amount, 0) AS outstanding_amount
        FROM invoice_outstanding io
        WHERE io.total_invoice - io.paid_amount > 0
    )
"""


# ============================================================================ #
#                     #SECTION - WORK MONITORING (PER WORK ITEM)               #
# ============================================================================ #

def get_v2_work_monitoring():
    """
    Satu baris per work item aktif (belum CLOSED) berikut deadline
    sesuai stage, tingkat reminder, lama di stage, dan status tertinggal.

    Aturan deadline:
      IDENTIFIED            -> target_end_date
      QUOTATION             -> valid_until penawaran terakhir
      CONTRACT              -> end_date kontrak, fallback target_end_date
      COMPLETED             -> tanggal selesai (BA harus segera dibuat)
      BA                    -> tanggal BA (invoice harus segera dibuat)
      INVOICE/PAYMENT       -> due_date invoice belum lunas paling awal
    """

    sql = f"""
        WITH {INVOICE_OUTSTANDING_CTE},

        unpaid_per_work AS (
            SELECT
                iu.id_work_item,
                MIN(iu.due_date) AS nearest_due_date,
                COUNT(*) AS unpaid_invoice_count,
                SUM(iu.outstanding_amount) AS outstanding_amount
            FROM invoice_unpaid iu
            GROUP BY iu.id_work_item
        ),

        work_data AS (
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

                -- Pekerjaan berkontrak dengan progress 100% dianggap COMPLETED.
                -- IN_PROGRESS tidak dipakai di V2, digabung ke CONTRACT.
                CASE
                    WHEN wi.current_stage IN ('CONTRACT', 'IN_PROGRESS')
                        AND wi.progress_percent >= 100
                        THEN 'COMPLETED'
                    WHEN wi.current_stage = 'IN_PROGRESS'
                        THEN 'CONTRACT'
                    ELSE wi.current_stage
                END AS current_stage,

                wi.progress_percent,
                wi.start_date,
                wi.target_end_date,

                COALESCE(wi.completion_date, comp.completion_date) AS completion_date,

                proposal.proposal_number,
                proposal.valid_until,

                contract.contract_number,
                contract.contract_start_date,
                contract.contract_end_date,

                comp.ba_number,
                comp.ba_date,

                upw.nearest_due_date,
                COALESCE(upw.unpaid_invoice_count, 0) AS unpaid_invoice_count,
                COALESCE(upw.outstanding_amount, 0) AS outstanding_amount,

                stage_now.stage_started_at,

                wi.updated_at

            FROM work_items wi

            LEFT JOIN client c
                ON c.id_client = wi.id_client

            LEFT JOIN client_pic cp
                ON cp.id_client_pic = wi.id_client_pic

            LEFT JOIN LATERAL (
                SELECT wp.proposal_number, wp.valid_until
                FROM work_proposals wp
                WHERE wp.id_work_item = wi.id_work_item
                    AND wp.is_active = 1
                ORDER BY wp.proposal_date DESC NULLS LAST, wp.created_at DESC
                LIMIT 1
            ) proposal ON TRUE

            LEFT JOIN LATERAL (
                SELECT
                    wc.contract_number,
                    wc.start_date AS contract_start_date,
                    wc.end_date AS contract_end_date
                FROM work_contracts wc
                WHERE wc.id_work_item = wi.id_work_item
                    AND wc.is_active = 1
                    AND wc.status <> 'CANCELLED'
                ORDER BY wc.contract_date DESC NULLS LAST, wc.created_at DESC
                LIMIT 1
            ) contract ON TRUE

            LEFT JOIN work_completions comp
                ON comp.id_work_item = wi.id_work_item
                AND comp.is_active = 1

            LEFT JOIN unpaid_per_work upw
                ON upw.id_work_item = wi.id_work_item

            LEFT JOIN LATERAL (
                SELECT wsh.started_at AS stage_started_at
                FROM work_stage_histories wsh
                WHERE wsh.id_work_item = wi.id_work_item
                    AND wsh.is_active = 1
                    AND wsh.ended_at IS NULL
                ORDER BY wsh.started_at DESC
                LIMIT 1
            ) stage_now ON TRUE

            WHERE
                wi.is_active = 1
                AND wi.current_stage <> 'CLOSED'
        ),

        deadline_data AS (
            SELECT
                wd.*,

                CASE
                    WHEN wd.current_stage = 'IDENTIFIED'
                        THEN wd.target_end_date

                    WHEN wd.current_stage = 'QUOTATION'
                        THEN wd.valid_until

                    WHEN wd.current_stage IN ('CONTRACT', 'IN_PROGRESS')
                        THEN COALESCE(wd.contract_end_date, wd.target_end_date)

                    WHEN wd.current_stage = 'COMPLETED'
                        THEN COALESCE(
                            wd.completion_date,
                            wd.stage_started_at::date
                        )

                    WHEN wd.current_stage = 'BA'
                        THEN COALESCE(
                            wd.ba_date,
                            wd.stage_started_at::date
                        )

                    WHEN wd.current_stage IN ('INVOICE', 'PAYMENT')
                        THEN wd.nearest_due_date

                    ELSE NULL
                END AS deadline_date,

                -- Persentase waktu berjalan untuk tahap pengerjaan
                CASE
                    WHEN wd.current_stage IN ('CONTRACT', 'IN_PROGRESS')
                        AND COALESCE(wd.contract_start_date, wd.start_date) IS NOT NULL
                        AND COALESCE(wd.contract_end_date, wd.target_end_date)
                            > COALESCE(wd.contract_start_date, wd.start_date)
                    THEN LEAST(GREATEST(ROUND(
                        (CURRENT_DATE - COALESCE(wd.contract_start_date, wd.start_date))::numeric
                        * 100
                        / (
                            COALESCE(wd.contract_end_date, wd.target_end_date)
                            - COALESCE(wd.contract_start_date, wd.start_date)
                        ),
                        2
                    ), 0), 100)
                    ELSE NULL
                END AS time_elapsed_percent

            FROM work_data wd
        ),

        final_data AS (
            SELECT
                dd.*,
                dd.deadline_date - CURRENT_DATE AS days_to_deadline,
                CURRENT_DATE - dd.stage_started_at::date AS days_in_stage,
                dd.contract_end_date - CURRENT_DATE AS days_to_contract_end
            FROM deadline_data dd
        )

        SELECT
            fd.*,

            {_reminder_level_sql("fd.days_to_deadline")} AS reminder_level,

            -- Status sisa waktu kontrak (dipakai kolom stage CONTRACT & COMPLETED)
            {_reminder_level_sql("fd.days_to_contract_end")} AS contract_end_level,

            CASE
                WHEN fd.time_elapsed_percent IS NULL THEN FALSE
                ELSE COALESCE(fd.progress_percent, 0) < fd.time_elapsed_percent
            END AS is_behind_schedule

        FROM final_data fd

        ORDER BY
            fd.days_to_deadline ASC NULLS LAST,
            fd.work_number ASC
    """

    with engine.connect() as conn:
        return conn.execute(text(sql)).mappings().all()


# ============================================================================ #
#                     #SECTION - UNPAID INVOICES (PER INVOICE)                 #
# ============================================================================ #

def get_v2_unpaid_invoices():
    """
    Satu baris per invoice yang masih punya sisa tagihan (termasuk PPN),
    hanya untuk work item aktif yang belum CLOSED.
    """

    sql = f"""
        WITH {INVOICE_OUTSTANDING_CTE}

        SELECT
            iu.id_invoice,
            iu.invoice_number,
            iu.invoice_date,
            iu.due_date,
            iu.total_invoice,
            iu.paid_amount,
            iu.outstanding_amount,

            wi.id_work_item,
            wi.work_number,
            wi.work_name,
            wi.work_type,
            wi.current_stage,
            wi.internal_pic_name,
            c.name AS client_name,

            iu.due_date - CURRENT_DATE AS days_to_deadline,

            {_reminder_level_sql("(iu.due_date - CURRENT_DATE)")} AS reminder_level

        FROM invoice_unpaid iu

        INNER JOIN work_items wi
            ON wi.id_work_item = iu.id_work_item

        LEFT JOIN client c
            ON c.id_client = wi.id_client

        WHERE
            wi.is_active = 1
            AND wi.current_stage <> 'CLOSED'

        ORDER BY
            iu.due_date ASC NULLS LAST,
            iu.invoice_number ASC
    """

    with engine.connect() as conn:
        return conn.execute(text(sql)).mappings().all()
