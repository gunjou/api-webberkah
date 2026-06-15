from sqlalchemy import text
from api.utils.config import engine


def get_attachment_list(id_invoice: int):
    sql = text("""
        SELECT
            a.id_attachment,
            a.id_invoice,
            a.id_attachment_type,

            t.kode,
            t.nama_type,

            a.nama_file,
            a.path_file,
            a.mime_type,
            a.ukuran_file,
            a.keterangan,

            a.created_at

        FROM attachments a

        LEFT JOIN ref_attachment_types t
            ON t.id_attachment_type =
               a.id_attachment_type

        WHERE a.id_invoice = :id_invoice
          AND a.status = 1

        ORDER BY
            a.id_attachment DESC
    """)

    with engine.connect() as conn:
        return conn.execute(
            sql,
            {
                "id_invoice": id_invoice
            }
        ).mappings().all()


def get_attachment_by_id(
    id_attachment: int
):
    sql = text("""
        SELECT
            a.*,

            t.kode,
            t.nama_type

        FROM attachments a

        LEFT JOIN ref_attachment_types t
            ON t.id_attachment_type =
               a.id_attachment_type

        WHERE a.id_attachment = :id_attachment
          AND a.status = 1

        LIMIT 1
    """)

    with engine.connect() as conn:
        return conn.execute(
            sql,
            {
                "id_attachment": id_attachment
            }
        ).mappings().first()


def create_attachment(
    id_invoice,
    id_attachment_type,
    nama_file,
    path_file,
    ukuran_file,
    mime_type,
    keterangan
):
    sql = text("""
        INSERT INTO attachments
        (
            id_invoice,
            id_attachment_type,

            nama_file,
            path_file,
            ukuran_file,
            mime_type,
            keterangan
        )
        VALUES
        (
            :id_invoice,
            :id_attachment_type,

            :nama_file,
            :path_file,
            :ukuran_file,
            :mime_type,
            :keterangan
        )

        RETURNING *
    """)

    with engine.begin() as conn:
        return conn.execute(
            sql,
            {
                "id_invoice": id_invoice,
                "id_attachment_type": id_attachment_type,
                "nama_file": nama_file,
                "path_file": path_file,
                "ukuran_file": ukuran_file,
                "mime_type": mime_type,
                "keterangan": keterangan
            }
        ).mappings().first()


def delete_attachment(
    id_attachment: int
):
    sql = text("""
        UPDATE attachments
        SET
            status = 0,
            updated_at = CURRENT_TIMESTAMP

        WHERE id_attachment = :id_attachment
          AND status = 1

        RETURNING id_attachment
    """)

    with engine.begin() as conn:
        return conn.execute(
            sql,
            {
                "id_attachment": id_attachment
            }
        ).mappings().first()
