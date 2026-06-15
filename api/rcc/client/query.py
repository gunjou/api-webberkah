from sqlalchemy import text
from api.utils.config import engine


def get_client_list():
    sql = text("""
        SELECT
            id_client,
            nama_client,
            alamat,
            telpon,
            email,
            keterangan,
            status,
            created_at,
            updated_at
        FROM client
        WHERE status = 1
        ORDER BY nama_client ASC
    """)

    with engine.connect() as conn:
        return conn.execute(sql).mappings().all()


def get_client_by_id(id_client: int):
    sql = text("""
        SELECT
            id_client,
            nama_client,
            alamat,
            telpon,
            email,
            keterangan,
            status,
            created_at,
            updated_at
        FROM client
        WHERE id_client = :id_client
          AND status = 1
        LIMIT 1
    """)

    with engine.connect() as conn:
        return conn.execute(
            sql,
            {"id_client": id_client}
        ).mappings().first()


def create_client(
    nama_client,
    alamat,
    telpon,
    email,
    keterangan
):
    sql = text("""
        INSERT INTO client
        (
            nama_client,
            alamat,
            telpon,
            email,
            keterangan
        )
        VALUES
        (
            :nama_client,
            :alamat,
            :telpon,
            :email,
            :keterangan
        )
        RETURNING *
    """)

    with engine.begin() as conn:
        return conn.execute(
            sql,
            {
                "nama_client": nama_client,
                "alamat": alamat,
                "telpon": telpon,
                "email": email,
                "keterangan": keterangan
            }
        ).mappings().first()


def update_client(
    id_client,
    nama_client,
    alamat,
    telpon,
    email,
    keterangan
):
    sql = text("""
        UPDATE client
        SET
            nama_client = :nama_client,
            alamat = :alamat,
            telpon = :telpon,
            email = :email,
            keterangan = :keterangan,
            updated_at = CURRENT_TIMESTAMP
        WHERE id_client = :id_client
          AND status = 1
        RETURNING *
    """)

    with engine.begin() as conn:
        return conn.execute(
            sql,
            {
                "id_client": id_client,
                "nama_client": nama_client,
                "alamat": alamat,
                "telpon": telpon,
                "email": email,
                "keterangan": keterangan
            }
        ).mappings().first()


def delete_client(id_client: int):
    sql = text("""
        UPDATE client
        SET
            status = 0,
            updated_at = CURRENT_TIMESTAMP
        WHERE id_client = :id_client
          AND status = 1
        RETURNING id_client
    """)

    with engine.begin() as conn:
        return conn.execute(
            sql,
            {"id_client": id_client}
        ).mappings().first()