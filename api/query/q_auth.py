from sqlalchemy import text
from api.utils.config import engine
from api.shared.helper import get_wita


# ======================================
# Fungsi untuk Login Admin
# ======================================
def get_admin_by_username(username: str):
    sql = text("""
        SELECT id_admin, username, password_hash, role, status
        FROM auth_admin
        WHERE username = :username
          AND status = 1
        LIMIT 1
    """)
    with engine.connect() as conn:
        return conn.execute(
            sql, {"username": username}
        ).mappings().first()

def update_admin_last_login(id_admin: int):
    sql = text("""
        UPDATE auth_admin
        SET last_login_at = :now,
            updated_at = :now
        WHERE id_admin = :id_admin
    """)
    with engine.begin() as conn:
        conn.execute(sql, {
            "id_admin": id_admin,
            "now": get_wita()
        })
        

# ======================================
# Fungsi untuk Login Pegawai
# ======================================
def get_pegawai_by_username(username: str):
    sql = text("""
        SELECT
            ap.id_auth_pegawai, ap.id_pegawai, ap.username, ap.password_hash, ap.img_path,
            ap.status AS auth_status, p.status AS pegawai_status
        FROM auth_pegawai ap
        JOIN pegawai p ON ap.id_pegawai = p.id_pegawai
        WHERE ap.username = :username
          AND ap.status = 1
        LIMIT 1
    """)
    with engine.connect() as conn:
        return conn.execute(
            sql, {"username": username}
        ).mappings().first()


def update_pegawai_last_login(id_auth_pegawai: int):
    sql = text("""
        UPDATE auth_pegawai
        SET last_login_at = :now,
            updated_at = :now
        WHERE id_auth_pegawai = :id_auth_pegawai
    """)
    with engine.begin() as conn:
        conn.execute(sql, {
            "id_auth_pegawai": id_auth_pegawai,
            "now": get_wita()
        })


# ======================================
# Fungsi untuk keperluan ganti password
# ======================================
def get_admin_password(id_admin: int):
    sql = text("""
        SELECT password_hash
        FROM auth_admin
        WHERE id_admin = :id_admin
          AND status = 1
        LIMIT 1
    """)
    with engine.connect() as conn:
        return conn.execute(
            sql, {"id_admin": id_admin}
        ).scalar()

def get_pegawai_password(id_pegawai: int):
    sql = text("""
        SELECT password_hash
        FROM auth_pegawai
        WHERE id_pegawai = :id_pegawai
          AND status = 1
        LIMIT 1
    """)
    with engine.connect() as conn:
        return conn.execute(
            sql, {"id_pegawai": id_pegawai}
        ).scalar()

def update_admin_password(id_admin: int, new_password_hash: str):
    sql = text("""
        UPDATE auth_admin
        SET password_hash = :password_hash,
            updated_at = :now
        WHERE id_admin = :id_admin
    """)
    with engine.begin() as conn:
        conn.execute(sql, {
            "id_admin": id_admin,
            "password_hash": new_password_hash,
            "now": get_wita()
        })

def update_pegawai_password(id_pegawai: int, new_password_hash: str):
    sql = text("""
        UPDATE auth_pegawai
        SET password_hash = :password_hash,
            updated_at = :now
        WHERE id_pegawai = :id_pegawai
    """)
    with engine.begin() as conn:
        conn.execute(sql, {
            "id_pegawai": id_pegawai,
            "password_hash": new_password_hash,
            "now": get_wita()
        })