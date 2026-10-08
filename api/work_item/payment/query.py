from sqlalchemy import text

from api.shared.exceptions import NotFoundError, ValidationError
from api.utils.config import engine
from api.shared.helper import get_wita


# ============================== CREATE PAYMENT ================================== #

def create_payment(id_invoice, payment_date, amount, document_url, notes, created_by):

    now = get_wita()

    with engine.begin() as conn:

        # ========================== LOCK INVOICE ========================== #

        invoice_query = text("""
            SELECT
                wi2.id_invoice,
                wi2.id_work_item,
                wi.current_stage,
                ROUND(
                    wi2.invoice_value
                    + (
                        wi2.invoice_value
                        * COALESCE(wi2.vat_rate, 0)
                        / 100
                    ),
                    2
                ) AS total_invoice
            FROM work_invoices wi2
            INNER JOIN work_items wi
                ON wi.id_work_item = wi2.id_work_item
               AND wi.is_active = 1
            WHERE wi2.id_invoice = :id_invoice
              AND wi2.is_active = 1
            FOR UPDATE
        """)

        invoice = conn.execute(
            invoice_query,
            {
                "id_invoice": id_invoice
            }
        ).mappings().first()

        if not invoice:
            raise NotFoundError("Invoice tidak ditemukan")

        # ============================ VALIDATE STAGE ============================ #

        if invoice["current_stage"] not in ("INVOICE", "PAYMENT"):
            raise ValidationError("Pembayaran tidak dapat ditambahkan pada stage saat ini")

        # =========================== PAYMENT TOTAL ============================= #

        payment_total_query = text("""
            SELECT
                COALESCE(
                    SUM(amount),
                    0
                ) AS total_paid
            FROM work_payments
            WHERE id_invoice = :id_invoice
              AND is_active = 1
        """)

        total_paid = conn.execute(
            payment_total_query,
            {
                "id_invoice": id_invoice
            }
        ).scalar() or 0

        outstanding_amount = max(
            invoice["total_invoice"] - total_paid,
            0
        )

        if amount > outstanding_amount:
            raise ValidationError("Nominal pembayaran melebihi sisa tagihan")

        # ============================ INSERT PAYMENT ============================ #

        insert_payment_query = text("""
            INSERT INTO work_payments (
                id_invoice, payment_date, amount, document_url, notes, is_active, created_by, created_at
            )
            VALUES (
                :id_invoice, :payment_date, :amount, :document_url, :notes, 1, :created_by, :created_at
            )
            RETURNING
                id_payment,
                id_invoice, payment_date, amount, document_url, notes, is_active, created_by, created_at
        """)

        payment = conn.execute(
            insert_payment_query,
            {
                "id_invoice": id_invoice,
                "payment_date": payment_date,
                "amount": amount,
                "document_url": document_url,
                "notes": notes,
                "created_by": created_by,
                "created_at": now
            }
        ).mappings().first()

        # ======================== FIRST PAYMENT ======================== #

        if invoice["current_stage"] == "INVOICE":

            # ======================== UPDATE WORK ITEM ======================== #

            update_work_query = text("""
                UPDATE work_items
                SET
                    current_stage = 'PAYMENT',
                    updated_by = :updated_by,
                    updated_at = :updated_at
                WHERE id_work_item = :id_work_item
                  AND is_active = 1
            """)

            conn.execute(
                update_work_query,
                {
                    "id_work_item": invoice["id_work_item"],
                    "updated_by": created_by,
                    "updated_at": now
                }
            )

            # ======================== INSERT HISTORY ======================== #

            insert_history_query = text("""
                INSERT INTO work_stage_histories (
                    id_work_item, stage, started_at, ended_at, notes, is_active, created_by, created_at
                )
                VALUES (
                    :id_work_item, 'PAYMENT', :started_at, NULL, :notes, 1, :created_by, :created_at
                )
            """)

            conn.execute(
                insert_history_query,
                {
                    "id_work_item": invoice["id_work_item"],
                    "started_at": now,
                    "notes": "Pembayaran pertama telah dibuat",
                    "created_by": created_by,
                    "created_at": now
                }
            )

        return dict(payment)


# ============================== PAYMENT DETAIL ================================ #

def get_payment_detail(id_payment):

    query = text("""
        SELECT
            wp.id_payment, wp.id_invoice, wi.id_work_item, wi.work_number, wi.work_name, wi.work_type, wi.current_stage, 
            wi.id_client, c.code AS client_code, c.name AS client_name, 
            wi2.invoice_number, wi2.invoice_date, wi2.invoice_value, wi2.vat_rate,
            ROUND(
                wi2.invoice_value
                * COALESCE(wi2.vat_rate, 0)
                / 100,
                2
            ) AS vat_amount,
            ROUND(
                wi2.invoice_value
                + (
                    wi2.invoice_value
                    * COALESCE(wi2.vat_rate, 0)
                    / 100
                ),
                2
            ) AS total_invoice,
            wi2.due_date, wp.payment_date, wp.amount, wp.document_url, wp.notes, 
            wp.is_active, wp.created_by, wp.created_at, wp.updated_by, wp.updated_at
        FROM work_payments wp
        INNER JOIN work_invoices wi2
            ON wi2.id_invoice = wp.id_invoice
           AND wi2.is_active = 1
        INNER JOIN work_items wi
            ON wi.id_work_item = wi2.id_work_item
           AND wi.is_active = 1
        LEFT JOIN client c
            ON c.id_client = wi.id_client
           AND c.is_active = 1
        WHERE wp.id_payment = :id_payment
          AND wp.is_active = 1
    """)

    with engine.connect() as conn:

        result = conn.execute(
            query,
            {
                "id_payment": id_payment
            }
        ).mappings().first()

    return dict(result) if result else None


# ============================== DELETE PAYMENT ================================ #

def delete_payment(id_payment, updated_by):

    now = get_wita()

    with engine.begin() as conn:

        # =========================== GET PAYMENT =========================== #

        payment_query = text("""
            SELECT
                wp.id_payment,
                wp.id_invoice,
                wi2.id_work_item,
                wi.current_stage
            FROM work_payments wp
            INNER JOIN work_invoices wi2
                ON wi2.id_invoice = wp.id_invoice
               AND wi2.is_active = 1
            INNER JOIN work_items wi
                ON wi.id_work_item = wi2.id_work_item
               AND wi.is_active = 1
            WHERE wp.id_payment = :id_payment
              AND wp.is_active = 1
            FOR UPDATE
        """)

        payment = conn.execute(
            payment_query,
            {
                "id_payment": id_payment
            }
        ).mappings().first()

        if not payment:
            return None

        # =========================== VALIDATE STAGE =========================== #

        if payment["current_stage"] not in ("PAYMENT"):
            raise ValidationError("Pembayaran tidak dapat dihapus pada stage saat ini")

        # ============================ DELETE PAYMENT =========================== #

        delete_query = text("""
            UPDATE work_payments
            SET
                is_active = 0,
                updated_by = :updated_by,
                updated_at = :updated_at

            WHERE id_payment = :id_payment
              AND is_active = 1
        """)

        conn.execute(
            delete_query,
            {
                "id_payment": id_payment,
                "updated_by": updated_by,
                "updated_at": now
            }
        )

        # ======================== CHECK ACTIVE PAYMENT ========================= #

        remaining_payment_query = text("""
            SELECT COUNT(*)
            FROM work_payments
            WHERE id_invoice = :id_invoice
              AND is_active = 1
        """)

        remaining_payment = conn.execute(
            remaining_payment_query,
            {
                "id_invoice": payment["id_invoice"]
            }
        ).scalar()

        # ====================================================================== #
        # Jika masih ada payment aktif, stage tetap PAYMENT
        # ====================================================================== #

        if remaining_payment > 0:

            return {
                "id_payment": id_payment,
                "id_invoice": payment["id_invoice"],
                "id_work_item": payment["id_work_item"],
                "current_stage": "PAYMENT"
            }

        # ====================================================================== #
        # Jika sudah tidak ada payment aktif:
        #
        # PAYMENT → INVOICE
        #
        # History lama tidak di-update.
        # Kita hanya INSERT history baru.
        # ====================================================================== #

        update_work_query = text("""
            UPDATE work_items
            SET
                current_stage = 'INVOICE',
                updated_by = :updated_by,
                updated_at = :updated_at

            WHERE id_work_item = :id_work_item
              AND is_active = 1
        """)

        conn.execute(
            update_work_query,
            {
                "id_work_item": payment["id_work_item"],
                "updated_by": updated_by,
                "updated_at": now
            }
        )

        # ========================== INSERT NEW HISTORY ========================== #

        insert_history_query = text("""
            INSERT INTO work_stage_histories (
                id_work_item, stage, started_at, ended_at, notes, is_active, created_by, created_at
            )
            VALUES (
                :id_work_item, 'INVOICE', :started_at, NULL, :notes, 1, :created_by, :created_at
            )
        """)

        conn.execute(
            insert_history_query,
            {
                "id_work_item": payment["id_work_item"],
                "started_at": now,
                "notes": "Pembayaran dihapus dan pekerjaan dikembalikan ke stage invoice",
                "created_by": updated_by,
                "created_at": now
            }
        )

        return {
            "id_payment": id_payment,
            "id_invoice": payment["id_invoice"],
            "id_work_item": payment["id_work_item"],
            "current_stage": "INVOICE"
        }