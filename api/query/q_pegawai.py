import os
from sqlalchemy import text
from api.shared.exceptions import NotFoundError, DatabaseError
from api.utils.config import engine
from api.shared.helper import _validate_image_file, extract_face_grayscale, get_wita, upload_face_to_cdn


# ==================================================
# FUNGSI HELPER VALIDASI PEGAWAI
# ==================================================
def is_pegawai_exists(id_pegawai: int):
    sql = text("""
        SELECT 1
        FROM pegawai
        WHERE id_pegawai = :id
          AND status = 1
        LIMIT 1
    """)
    with engine.connect() as conn:
        return conn.execute(sql, {"id": id_pegawai}).first() is not None


def get_auth_pegawai_by_pegawai_id(id_pegawai: int):
    sql = text("""
        SELECT id_auth_pegawai
        FROM auth_pegawai
        WHERE id_pegawai = :id
          AND status = 1
        LIMIT 1
    """)
    with engine.connect() as conn:
        return conn.execute(sql, {"id": id_pegawai}).first()


def is_nip_exists(nip: str):
    sql = text("""
        SELECT 1
        FROM pegawai
        WHERE nip = :nip
        LIMIT 1
    """)
    with engine.connect() as conn:
        return conn.execute(sql, {"nip": nip}).first() is not None


def is_username_exists(username: str):
    sql = text("""
        SELECT 1
        FROM auth_pegawai
        WHERE username = :username
        LIMIT 1
    """)
    with engine.connect() as conn:
        return conn.execute(sql, {"username": username}).first() is not None

def get_lokasi_pegawai(id_pegawai: int):
    sql = text("""
        SELECT id_lokasi, status
        FROM pegawai_lokasi_absensi
        WHERE id_pegawai = :id
    """)
    with engine.connect() as conn:
        return conn.execute(sql, {"id": id_pegawai}).mappings().all()



# ==================================================
# ALL DATA PEGAWAI
# ==================================================
def get_all_pegawai_core():
    sql = text("""
        SELECT
            p.id_pegawai, p.nip, p.nama_lengkap, p.nama_panggilan, p.jenis_kelamin, p.tanggal_masuk,

            d.id_departemen, d.nama_departemen, j.id_jabatan, j.nama_jabatan, lj.id_level_jabatan, lj.nama_level as level_jabatan,
            sp.id_status_pegawai, sp.nama_status AS status_pegawai,

            pr.nik, pr.alamat, pr.no_telepon, pr.email_pribadi, pr.tempat_lahir, pr.tanggal_lahir,
            pr.image_path, pr.agama, pr.status_nikah,

            r.nama_bank, r.no_rekening, r.atas_nama,

            ap.username, ap.kode_pemulihan, ap.img_path, ap.status AS auth_status, ap.last_login_at

        FROM pegawai p
        LEFT JOIN ref_departemen d ON d.id_departemen = p.id_departemen
        LEFT JOIN ref_jabatan j ON j.id_jabatan = p.id_jabatan
        LEFT JOIN ref_level_jabatan lj ON lj.id_level_jabatan = p.id_level_jabatan
        LEFT JOIN ref_status_pegawai sp ON sp.id_status_pegawai = p.id_status_pegawai

        LEFT JOIN pegawai_pribadi pr ON pr.id_pegawai = p.id_pegawai AND pr.status = 1
        LEFT JOIN pegawai_rekening r ON r.id_pegawai = p.id_pegawai AND r.status = 1
        LEFT JOIN auth_pegawai ap ON ap.id_pegawai = p.id_pegawai AND ap.status = 1

        WHERE p.status = 1
        ORDER BY p.tanggal_masuk ASC, p.id_pegawai ASC
    """)

    with engine.connect() as conn:
        return conn.execute(sql).mappings().all()
    
    
def get_pendidikan_by_pegawai(id_pegawai: int):
    sql = text("""
        SELECT
            jenjang, institusi, jurusan, tahun_masuk, tahun_lulus
        FROM pegawai_pendidikan
        WHERE id_pegawai = :id
          AND status = 1
        ORDER BY tahun_lulus DESC
    """)
    with engine.connect() as conn:
        return conn.execute(sql, {"id": id_pegawai}).mappings().fetchone()
    
    
def get_lokasi_absensi_by_pegawai(id_pegawai: int):
    sql = text("""
        SELECT
            l.id_lokasi, l.nama_lokasi, l.latitude, l.longitude, l.radius_meter
        FROM pegawai_lokasi_absensi pla
        JOIN ref_lokasi_absensi l ON l.id_lokasi = pla.id_lokasi
        WHERE pla.id_pegawai = :id
          AND pla.status = 1
          AND l.status = 1
    """)
    with engine.connect() as conn:
        return conn.execute(sql, {"id": id_pegawai}).mappings().all()



# ==================================================
# GET DATA PEGAWAI PER TAB
# ==================================================
def get_pegawai_profile():
    """
    Ambil data profile pegawai (CORE TAB)
    """
    sql = text("""
        SELECT
            p.id_pegawai, p.nip, p.nama_lengkap, p.nama_panggilan, p.jenis_kelamin, p.tanggal_masuk,
            p.id_status_pegawai, p.id_jabatan, p.id_departemen, p.id_level_jabatan,
            
            sp.nama_status AS status_pegawai, j.nama_jabatan, d.nama_departemen, lj.nama_level AS level_jabatan,

            pr.nik, pr.agama, pr.tempat_lahir, pr.tanggal_lahir, pr.status_nikah, pr.email_pribadi, pr.no_telepon, 
            pr.alamat

        FROM pegawai p
        LEFT JOIN ref_status_pegawai sp
            ON sp.id_status_pegawai = p.id_status_pegawai
        LEFT JOIN ref_jabatan j
            ON j.id_jabatan = p.id_jabatan
        LEFT JOIN ref_departemen d
            ON d.id_departemen = p.id_departemen
        LEFT JOIN ref_level_jabatan lj
            ON lj.id_level_jabatan = p.id_level_jabatan
        LEFT JOIN pegawai_pribadi pr
            ON pr.id_pegawai = p.id_pegawai
           AND pr.status = 1
        WHERE p.status = 1
        ORDER BY p.tanggal_masuk ASC, p.id_pegawai ASC
    """)
    with engine.connect() as conn:
        return conn.execute(sql).mappings().all()


def get_pegawai_rekening():
    """
    Ambil data rekening pegawai (TAB REKENING)
    """
    sql = text("""
        SELECT
            p.id_pegawai, p.nip, p.nama_lengkap, p.tanggal_masuk, sp.nama_status AS status_pegawai, 
            r.nama_bank, r.no_rekening, r.atas_nama
        FROM pegawai p
        LEFT JOIN ref_status_pegawai sp
            ON sp.id_status_pegawai = p.id_status_pegawai
        LEFT JOIN pegawai_rekening r
            ON r.id_pegawai = p.id_pegawai
           AND r.status = 1
        WHERE p.status = 1
        ORDER BY p.tanggal_masuk ASC, p.id_pegawai ASC
    """)
    with engine.connect() as conn:
        return conn.execute(sql).mappings().all()
    

def get_pegawai_pendidikan():
    """
    Ambil data pendidikan pegawai (TAB PENDIDIKAN)
    """
    sql = text("""
        SELECT
            p.id_pegawai, p.nip, p.nama_lengkap, p.tanggal_masuk, sp.nama_status AS status_pegawai,
            pd.jenjang, pd.institusi, pd.jurusan, pd.tahun_masuk, pd.tahun_lulus
        FROM pegawai p
        LEFT JOIN ref_status_pegawai sp
            ON sp.id_status_pegawai = p.id_status_pegawai
        LEFT JOIN pegawai_pendidikan pd
            ON pd.id_pegawai = p.id_pegawai
           AND pd.status = 1
        WHERE p.status = 1
        ORDER BY p.tanggal_masuk ASC, p.id_pegawai ASC
    """)
    with engine.connect() as conn:
        return conn.execute(sql).mappings().all()


def get_pegawai_akun():
    """
    Ambil data akun sistem pegawai (TAB AKUN)
    """
    sql = text("""
        SELECT
            p.id_pegawai, p.nip, p.nama_lengkap, p.tanggal_masuk, sp.nama_status AS status_pegawai,
            ap.username, ap.kode_pemulihan, ap.img_path, ap.last_login_at, ap.status AS auth_status
        FROM pegawai p
        LEFT JOIN ref_status_pegawai sp
            ON sp.id_status_pegawai = p.id_status_pegawai
        LEFT JOIN auth_pegawai ap
            ON ap.id_pegawai = p.id_pegawai
        WHERE p.status = 1
        ORDER BY p.tanggal_masuk ASC, p.id_pegawai ASC
    """)
    with engine.connect() as conn:
        return conn.execute(sql).mappings().all()


def get_pegawai_lokasi():
    """
    Ambil data lokasi absensi pegawai (TAB LOKASI)
    """
    sql = text("""
        SELECT
            p.id_pegawai, p.nip, p.nama_lengkap, p.tanggal_masuk, sp.nama_status AS status_pegawai,
            la.id_lokasi, la.nama_lokasi, la.latitude, la.longitude, la.radius_meter
        FROM pegawai p
        LEFT JOIN ref_status_pegawai sp
            ON sp.id_status_pegawai = p.id_status_pegawai
        LEFT JOIN pegawai_lokasi_absensi pla
            ON pla.id_pegawai = p.id_pegawai
           AND pla.status = 1
        LEFT JOIN ref_lokasi_absensi la
            ON la.id_lokasi = pla.id_lokasi
           AND la.status = 1
        WHERE p.status = 1
        ORDER BY p.tanggal_masuk ASC, p.id_pegawai ASC
    """)
    with engine.connect() as conn:
        return conn.execute(sql).mappings().all()



# ==================================================
# REGISTER PEGAWAI BARU
# ==================================================
def register_pegawai(
    nama_lengkap,
    nip,
    jenis_kelamin,
    tanggal_masuk,
    id_departemen,
    id_jabatan,
    id_level_jabatan,
    id_status_pegawai,
    username,
    password_hash,
    kode_pemulihan
):
    with engine.begin() as conn:
        # insert pegawai
        pegawai_sql = text("""
            INSERT INTO pegawai (
                nama_lengkap, nip, jenis_kelamin, tanggal_masuk, id_departemen, id_jabatan, id_level_jabatan, id_status_pegawai
            ) VALUES (
                :nama_lengkap, :nip, :jenis_kelamin, :tanggal_masuk, :id_departemen, :id_jabatan, :id_level_jabatan, :id_status_pegawai
            )
            RETURNING id_pegawai
        """)

        id_pegawai = conn.execute(pegawai_sql, {
            "nama_lengkap": nama_lengkap,
            "nip": nip,
            "jenis_kelamin": jenis_kelamin,
            "tanggal_masuk": tanggal_masuk,
            "id_departemen": id_departemen,
            "id_jabatan": id_jabatan,
            "id_level_jabatan": id_level_jabatan,
            "id_status_pegawai": id_status_pegawai,
        }).scalar()

        # insert auth pegawai
        auth_sql = text("""
            INSERT INTO auth_pegawai (
                id_pegawai, username, password_hash, kode_pemulihan, created_at, updated_at
            ) VALUES (
                :id_pegawai, :username, :password_hash, :kode_pemulihan, :now, :now
            )
        """)

        conn.execute(auth_sql, {
            "id_pegawai": id_pegawai,
            "username": username,
            "password_hash": password_hash,
            "kode_pemulihan": kode_pemulihan,
            "now": get_wita()
        })

        return id_pegawai


# ==================================================
# UPDATE DAN INSERT DATA PEGAWAI PRIBADI
# ==================================================
def update_pegawai_lengkap(id_pegawai: int, pegawai_data: dict, pribadi_data: dict):
    with engine.begin() as conn:
        sql_pegawai = text("""
            UPDATE pegawai
            SET
                nip = :nip,
                nama_lengkap = :nama_lengkap,
                nama_panggilan = :nama_panggilan,
                jenis_kelamin = :jenis_kelamin,
                tanggal_masuk = :tanggal_masuk,
                id_departemen = :id_departemen,
                id_jabatan = :id_jabatan,
                id_level_jabatan = :id_level_jabatan,
                id_status_pegawai = :id_status_pegawai,
                updated_at = :now
            WHERE id_pegawai = :id_pegawai
              AND status = 1
        """)

        conn.execute(sql_pegawai, {
            **pegawai_data,
            "id_pegawai": id_pegawai,
            "now": get_wita()
        })

        id_pribadi = conn.execute(
            text("""
                SELECT id_pribadi
                FROM pegawai_pribadi
                WHERE id_pegawai = :id
                  AND status = 1
                LIMIT 1
            """),
            {"id": id_pegawai}
        ).scalar()

        if id_pribadi:
            # UPDATE
            sql_update = text("""
                UPDATE pegawai_pribadi
                SET
                    nik = :nik,
                    alamat = :alamat,
                    no_telepon = :no_telepon,
                    email_pribadi = :email_pribadi,
                    tempat_lahir = :tempat_lahir,
                    tanggal_lahir = :tanggal_lahir,
                    agama = :agama,
                    status_nikah = :status_nikah,
                    updated_at = :now
                WHERE id_pegawai = :id_pegawai
                  AND status = 1
            """)

            conn.execute(sql_update, {
                **pribadi_data,
                "id_pegawai": id_pegawai,
                "now": get_wita()
            })

        else:
            # INSERT
            sql_insert = text("""
                INSERT INTO pegawai_pribadi (
                    id_pegawai, nik, alamat, no_telepon, email_pribadi, tempat_lahir, tanggal_lahir, 
                    agama, status_nikah, created_at, updated_at
                ) VALUES (
                    :id_pegawai, :nik, :alamat, :no_telepon, :email_pribadi, :tempat_lahir, :tanggal_lahir, 
                    :agama, :status_nikah, :now, :now
                )
            """)

            conn.execute(sql_insert, {
                **pribadi_data,
                "id_pegawai": id_pegawai,
                "now": get_wita()
            })



# ==================================================
# UPDATE DAN INSERT REKENING PEGAWAI
# ==================================================
def upsert_pegawai_rekening(id_pegawai: int, nama_bank: str, no_rekening: str, atas_nama: str):
    with engine.begin() as conn:

        # cek rekening existing
        id_rekening = conn.execute(
            text("""
                SELECT id_rekening
                FROM pegawai_rekening
                WHERE id_pegawai = :id
                  AND status = 1
                LIMIT 1
            """),
            {"id": id_pegawai}
        ).scalar()

        if id_rekening:
            # UPDATE
            sql_update = text("""
                UPDATE pegawai_rekening
                SET
                    nama_bank = :nama_bank,
                    no_rekening = :no_rekening,
                    atas_nama = :atas_nama,
                    updated_at = :now
                WHERE id_pegawai = :id_pegawai
                  AND status = 1
            """)

            conn.execute(sql_update, {
                "id_pegawai": id_pegawai,
                "nama_bank": nama_bank,
                "no_rekening": no_rekening,
                "atas_nama": atas_nama,
                "now": get_wita()
            })

        else:
            # INSERT
            sql_insert = text("""
                INSERT INTO pegawai_rekening (
                    id_pegawai, nama_bank, no_rekening, atas_nama, created_at, updated_at
                )
                VALUES (
                    :id_pegawai, :nama_bank, :no_rekening, :atas_nama, :now, :now
                )
            """)

            conn.execute(sql_insert, {
                "id_pegawai": id_pegawai,
                "nama_bank": nama_bank,
                "no_rekening": no_rekening,
                "atas_nama": atas_nama,
                "now": get_wita()
            })



# ==================================================
# UPDATE DAN INSERT PEDIDIKAN PEGAWAI
# ==================================================
def upsert_pegawai_pendidikan(
    id_pegawai: int,
    jenjang: str,
    institusi: str,
    jurusan: str,
    tahun_masuk: int | None,
    tahun_lulus: int | None
):
    with engine.begin() as conn:

        # cek pendidikan existing
        id_pendidikan = conn.execute(
            text("""
                SELECT id_pendidikan
                FROM pegawai_pendidikan
                WHERE id_pegawai = :id
                  AND status = 1
                LIMIT 1
            """),
            {"id": id_pegawai}
        ).scalar()

        if id_pendidikan:
            # UPDATE
            sql_update = text("""
                UPDATE pegawai_pendidikan
                SET
                    jenjang = :jenjang,
                    institusi = :institusi,
                    jurusan = :jurusan,
                    tahun_masuk = :tahun_masuk,
                    tahun_lulus = :tahun_lulus,
                    updated_at = :now
                WHERE id_pegawai = :id_pegawai
                  AND status = 1
            """)

            conn.execute(sql_update, {
                "id_pegawai": id_pegawai,
                "jenjang": jenjang,
                "institusi": institusi,
                "jurusan": jurusan,
                "tahun_masuk": tahun_masuk,
                "tahun_lulus": tahun_lulus,
                "now": get_wita()
            })

        else:
            # INSERT
            sql_insert = text("""
                INSERT INTO pegawai_pendidikan (
                    id_pegawai, jenjang, institusi, jurusan, tahun_masuk, tahun_lulus, created_at, updated_at
                )
                VALUES (
                    :id_pegawai, :jenjang, :institusi, :jurusan, :tahun_masuk, :tahun_lulus, :now, :now
                )
            """)

            conn.execute(sql_insert, {
                "id_pegawai": id_pegawai,
                "jenjang": jenjang,
                "institusi": institusi,
                "jurusan": jurusan,
                "tahun_masuk": tahun_masuk,
                "tahun_lulus": tahun_lulus,
                "now": get_wita()
            })



# ==================================================
# UPDATE WAJAH PEGAWAI UNTUK VERIFIKASI ABSENSI
# ==================================================
def enroll_face_pegawai(id_pegawai: int, file):
    _validate_image_file(file)

    auth = get_auth_pegawai_by_pegawai_id(id_pegawai)
    if not auth:
        raise NotFoundError("Akun pegawai belum tersedia")

    face_path = extract_face_grayscale(file)

    try:
        img_url = upload_face_to_cdn(face_path)

        sql = text("""
            UPDATE auth_pegawai
            SET img_path = :img_path,
                updated_at = :now
            WHERE id_pegawai = :id_pegawai
              AND status = 1
        """)

        with engine.begin() as conn:
            result = conn.execute(sql, {
                "id_pegawai": id_pegawai,
                "img_path": img_url,
                "now": get_wita()
            })

            if result.rowcount == 0:
                raise DatabaseError("Gagal memperbarui foto pegawai")

        return img_url

    finally:
        if os.path.exists(face_path):
            os.remove(face_path)



# ==================================================
# RESET PASSWORD PEGAWAI LANGSUNG OLEH ADMIN
# ==================================================
def reset_password_pegawai(
    id_pegawai: int,
    password_hash: str
):
    sql = text("""
        UPDATE auth_pegawai
        SET
            password_hash = :password_hash,
            updated_at = :now
        WHERE id_pegawai = :id_pegawai
          AND status = 1
    """)
    with engine.begin() as conn:
        result = conn.execute(sql, {
            "id_pegawai": id_pegawai,
            "password_hash": password_hash,
            "now": get_wita()
        })
        return result.rowcount
    
    
    
# ==================================================
# SINKRONISASI LOKASI ABSENSI PEGAWAI
# ==================================================
def sync_lokasi_pegawai(id_pegawai: int, id_lokasi_list: list[int]):
    with engine.begin() as conn:

        # ambil lokasi existing
        rows = conn.execute(
            text("""
                SELECT id_lokasi, status
                FROM pegawai_lokasi_absensi
                WHERE id_pegawai = :id
            """),
            {"id": id_pegawai}
        ).mappings().all()

        existing_map = {
            row["id_lokasi"]: row["status"]
            for row in rows
        }

        now = get_wita()

        # 1️⃣ nonaktifkan lokasi yang tidak ada di payload
        for id_lokasi in existing_map:
            if id_lokasi not in id_lokasi_list:
                conn.execute(
                    text("""
                        UPDATE pegawai_lokasi_absensi
                        SET status = 0,
                            updated_at = :now
                        WHERE id_pegawai = :id_pegawai
                          AND id_lokasi = :id_lokasi
                    """),
                    {
                        "id_pegawai": id_pegawai,
                        "id_lokasi": id_lokasi,
                        "now": now
                    }
                )

        # 2️⃣ aktifkan / insert lokasi dari payload
        for id_lokasi in id_lokasi_list:
            if id_lokasi in existing_map:
                # aktifkan kembali jika sebelumnya nonaktif
                conn.execute(
                    text("""
                        UPDATE pegawai_lokasi_absensi
                        SET status = 1,
                            updated_at = :now
                        WHERE id_pegawai = :id_pegawai
                          AND id_lokasi = :id_lokasi
                    """),
                    {
                        "id_pegawai": id_pegawai,
                        "id_lokasi": id_lokasi,
                        "now": now
                    }
                )
            else:
                # insert baru
                conn.execute(
                    text("""
                        INSERT INTO pegawai_lokasi_absensi (
                            id_pegawai, id_lokasi, status, created_at, updated_at
                        )
                        VALUES (
                            :id_pegawai, :id_lokasi, 1, :now, :now
                        )
                    """),
                    {
                        "id_pegawai": id_pegawai,
                        "id_lokasi": id_lokasi,
                        "now": now
                    }
                )



# ==================================================
# NONAKTIFKAN PEGAWAI & NONAKTIFKAN AKUN LOGIN
# ==================================================
def soft_delete_pegawai(id_pegawai: int):
    with engine.begin() as conn:
        now = get_wita()

        # nonaktifkan pegawai
        result = conn.execute(
            text("""
                UPDATE pegawai
                SET status = 0,
                    updated_at = :now
                WHERE id_pegawai = :id
                  AND status = 1
            """),
            {
                "id": id_pegawai,
                "now": now
            }
        )

        return result.rowcount
