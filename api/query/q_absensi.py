from sqlalchemy import text
from api.utils.config import engine
from api.shared.helper import get_wita


# ==================================================
# FUNGSI HELPER UNTUK KEPERLUAN ABSENSI
# ==================================================
def get_all_lokasi_absensi():
    sql = text("""
        SELECT
            id_lokasi, nama_lokasi, latitude, longitude, radius_meter
        FROM ref_lokasi_absensi
        WHERE status = 1
    """)
    with engine.connect() as conn:
        return conn.execute(sql).mappings().all()

def get_allowed_lokasi_ids_pegawai(id_pegawai: int) -> set[int]:
    sql = text("""
        SELECT id_lokasi
        FROM pegawai_lokasi_absensi
        WHERE id_pegawai = :id
          AND status = 1
    """)
    with engine.connect() as conn:
        rows = conn.execute(sql, {"id": id_pegawai}).scalars().all()
        return set(rows)


# HELPER UNTUK ISTIRAHAT MULAI DAN ISTIRAHAT SELESAI
def get_absensi_hari_ini(id_pegawai: int, tanggal):
    sql = text("""
        SELECT id_absensi, jam_keluar
        FROM absensi
        WHERE id_pegawai = :id
          AND tanggal = :tanggal
          AND status = 1
        LIMIT 1
    """)
    with engine.connect() as conn:
        return conn.execute(sql, {
            "id": id_pegawai,
            "tanggal": tanggal
        }).mappings().first()

# HELPER UNTUK ISTIRAHAT SELESAI DAN CHECKOUT
def get_active_istirahat(id_absensi: int):
    sql = text("""
        SELECT
            id_istirahat,
            jam_mulai
        FROM absensi_istirahat
        WHERE id_absensi = :id_absensi
          AND jam_mulai IS NOT NULL
          AND jam_selesai IS NULL
          AND status = 1
        LIMIT 1
    """)
    with engine.connect() as conn:
        return conn.execute(
            sql, {"id_absensi": id_absensi}
        ).mappings().first()

# HELPER UNTUK MENDAPATKAN APAKAH PEGAWAI BOLEH PILIH SHIFT
def has_active_shift(id_pegawai: int) -> bool:
    sql = text("""
        SELECT 1
        FROM pegawai_jam_kerja
        WHERE id_pegawai = :id_pegawai
          AND status = 1
        LIMIT 1
    """)
    with engine.connect() as conn:
        return conn.execute(
            sql, {"id_pegawai": id_pegawai}
        ).first() is not None

# HELPER UNTUK MENDAPATKAN JAM MULAI KERJA YANG DIHITUNG UNTUK KETERLAMBATAN
def is_valid_jam_kerja_pegawai(id_pegawai: int, id_jam_kerja: int) -> bool:
    """Cek apakah pegawai boleh mengambil jam kerja ini"""
    # Shift normal (id=1) selalu valid
    if id_jam_kerja == 1:
        return True

    sql = text("""
        SELECT 1
        FROM pegawai_jam_kerja
        WHERE id_pegawai = :id_pegawai
          AND id_jam_kerja = :id_jam_kerja
          AND status = 1
        LIMIT 1
    """)
    with engine.connect() as conn:
        return conn.execute(
            sql,
            {
                "id_pegawai": id_pegawai,
                "id_jam_kerja": id_jam_kerja
            }
        ).first() is not None

# MENGAMBIL DATA PEGAWAI YANG DIIZINKAN WFH
def is_pegawai_wfh(id_pegawai: int) -> bool:
    """
    Cek apakah pegawai diizinkan WFH
    """
    sql = text("""
        SELECT 1
        FROM pegawai_wfh
        WHERE id_pegawai = :id_pegawai
          AND status = 1
        LIMIT 1
    """)
    with engine.connect() as conn:
        return conn.execute(
            sql, {"id_pegawai": id_pegawai}
        ).first() is not None



# ==================================================
# GET ABSENSI HARIAN UNTUK KEPERLUAN ABSEN
# ==================================================
def get_absensi_harian(id_pegawai: int, tanggal):
    """
    Ambil data absensi harian pegawai
    """
    sql = text("""
        SELECT
            p.id_pegawai, p.nama_lengkap, p.nama_panggilan, a.id_absensi, a.tanggal, a.jam_masuk, a.jam_keluar, 
            a.menit_terlambat, a.id_jam_kerja,
            jk.nama_shift, jk.jam_per_hari, jk.jam_mulai, jk.jam_selesai, 
            lm.nama_lokasi AS lokasi_masuk, lk.nama_lokasi AS lokasi_keluar
        FROM pegawai p
        LEFT JOIN absensi a
            ON a.id_pegawai = p.id_pegawai
           AND a.tanggal = :tanggal
           AND a.status = 1
        LEFT JOIN ref_jam_kerja jk
            ON jk.id_jam_kerja = a.id_jam_kerja
        LEFT JOIN ref_lokasi_absensi lm
            ON lm.id_lokasi = a.id_lokasi_masuk
        LEFT JOIN ref_lokasi_absensi lk
            ON lk.id_lokasi = a.id_lokasi_keluar
        WHERE p.id_pegawai = :id_pegawai
          AND p.status = 1
        LIMIT 1
    """)
    with engine.connect() as conn:
        return conn.execute(
            sql,
            {
                "id_pegawai": id_pegawai,
                "tanggal": tanggal
            }
        ).mappings().first()


def get_active_absensi_untuk_harian(id_pegawai: int):
    sql = text("""
        SELECT
            a.id_absensi, a.tanggal, a.jam_masuk, a.jam_keluar, a.menit_terlambat, a.total_menit_istirahat, 
            a.id_jam_kerja, p.id_pegawai, p.nama_lengkap, p.nama_panggilan,

            jk.nama_shift, jk.jam_per_hari, jk.jam_mulai, jk.jam_selesai,

            lm.nama_lokasi AS lokasi_masuk,
            lk.nama_lokasi AS lokasi_keluar

        FROM absensi a
        JOIN pegawai p ON p.id_pegawai = a.id_pegawai
        LEFT JOIN ref_jam_kerja jk ON jk.id_jam_kerja = a.id_jam_kerja
        LEFT JOIN ref_lokasi_absensi lm ON lm.id_lokasi = a.id_lokasi_masuk
        LEFT JOIN ref_lokasi_absensi lk ON lk.id_lokasi = a.id_lokasi_keluar
        WHERE a.id_pegawai = :id_pegawai
          AND a.jam_keluar IS NULL
          AND a.status = 1
        ORDER BY a.tanggal DESC
        LIMIT 1
    """)
    with engine.connect() as conn:
        return conn.execute(sql, {"id_pegawai": id_pegawai}).mappings().first()


# HELPER UNTUK GET DATA ABSENSI HARIAN
def get_istirahat_absensi(id_absensi: int):
    """
    Ambil data istirahat absensi
    """
    sql = text("""
        SELECT
            ai.jam_mulai, ai.jam_selesai, ai.durasi_menit, lb.nama_lokasi AS lokasi_balik
        FROM absensi_istirahat ai
        LEFT JOIN ref_lokasi_absensi lb
            ON lb.id_lokasi = ai.id_lokasi_balik
        WHERE ai.id_absensi = :id_absensi
          AND ai.status = 1
        ORDER BY ai.jam_mulai ASC
    """)
    with engine.connect() as conn:
        return conn.execute(
            sql,
            {"id_absensi": id_absensi}
        ).mappings().all()
        
        
        
# ==================================================
# ABSENSI MASUK UNTUK PEGAWAI
# ==================================================

# HELPER UNTUK VALIDASI CHECKIN APAKAH SUDAH CHECKIN ATAU TIDAK
def is_already_checkin(id_pegawai: int) -> bool:
    """
    Cek apakah pegawai masih memiliki absensi aktif
    (belum checkout)
    """
    sql = text("""
        SELECT 1
        FROM absensi
        WHERE id_pegawai = :id_pegawai
          AND jam_keluar IS NULL
          AND status = 1
        LIMIT 1
    """)
    with engine.connect() as conn:
        return conn.execute(
            sql, {"id_pegawai": id_pegawai}
        ).first() is not None

def get_jam_kerja_by_id(id_jam_kerja: int):
    sql = text("""
        SELECT
            id_jam_kerja, nama_shift, jam_mulai, jam_selesai, jam_per_hari
        FROM ref_jam_kerja
        WHERE id_jam_kerja = :id_jam_kerja
          AND status = 1
        LIMIT 1
    """)
    with engine.connect() as conn:
        return conn.execute(
            sql,
            {"id_jam_kerja": id_jam_kerja}
        ).mappings().first()

def insert_absensi_masuk(
    id_pegawai: int, tanggal, jam_masuk, id_lokasi_masuk: int, id_jam_kerja: int, menit_terlambat: int
):
    sql = text("""
        INSERT INTO absensi (
            id_pegawai, tanggal, id_jam_kerja, jam_masuk, id_lokasi_masuk, menit_terlambat, status, created_at, updated_at
        )
        VALUES (
            :id_pegawai, :tanggal, :id_jam_kerja, :jam_masuk, :id_lokasi_masuk, :menit_terlambat, 1, :now, :now
        )
        RETURNING id_absensi
    """)
    with engine.begin() as conn:
        return conn.execute(sql, {
            "id_pegawai": id_pegawai,
            "tanggal": tanggal,
            "id_jam_kerja": id_jam_kerja,
            "jam_masuk": jam_masuk,
            "id_lokasi_masuk": id_lokasi_masuk,
            "menit_terlambat": menit_terlambat,
            "now": get_wita()
        }).scalar()


# HELPER UNTUK VALIDASI CHECKOUT KALAU SUDAH CHECKIN
def get_active_absensi(id_pegawai: int):
    """
    Ambil absensi aktif (belum checkout),
    berlaku untuk semua jenis shift (normal & malam)
    """
    sql = text("""
        SELECT
            a.id_absensi, a.tanggal, a.jam_masuk, a.total_menit_istirahat, a.id_jam_kerja
        FROM absensi a
        WHERE a.id_pegawai = :id_pegawai
          AND a.jam_keluar IS NULL
          AND a.status = 1
        ORDER BY a.tanggal DESC
        LIMIT 1
    """)
    with engine.connect() as conn:
        return conn.execute(
            sql, {"id_pegawai": id_pegawai}
        ).mappings().first()
        
def update_absensi_checkout(id_absensi: int, jam_keluar, id_lokasi_keluar: int, total_menit_kerja: int):
    sql = text("""
        UPDATE absensi
        SET
            jam_keluar = :jam_keluar,
            id_lokasi_keluar = :id_lokasi_keluar,
            total_menit_kerja = :total_menit_kerja,
            updated_at = :now
        WHERE id_absensi = :id_absensi
    """)
    with engine.begin() as conn:
        conn.execute(sql, {
            "id_absensi": id_absensi,
            "jam_keluar": jam_keluar,
            "id_lokasi_keluar": id_lokasi_keluar,
            "total_menit_kerja": total_menit_kerja,
            "now": get_wita()
        })
        


# ==================================================
# ABSENSI ISTIRAHAT UNTUK PEGAWAI
# ==================================================

# FUNGSI ISTIRAHAT MULAI
def insert_istirahat_mulai(id_absensi: int, jam_mulai):
    sql = text("""
        INSERT INTO absensi_istirahat (
            id_absensi, jam_mulai, status, created_at, updated_at
        )
        VALUES (
            :id_absensi, :jam_mulai, 1, :now, :now
        )
        RETURNING id_istirahat
    """)
    with engine.begin() as conn:
        return conn.execute(sql, {
            "id_absensi": id_absensi,
            "jam_mulai": jam_mulai,
            "now": get_wita()
        }).scalar()


# FUNGSI ISTIRAHAT SELESAI
def update_istirahat_selesai(id_istirahat: int, jam_selesai, durasi_menit: int, id_lokasi_balik: int):
    sql = text("""
        UPDATE absensi_istirahat
        SET jam_selesai = :jam_selesai,
            durasi_menit = :durasi_menit,
            id_lokasi_balik = :id_lokasi_balik,
            updated_at = :now
        WHERE id_istirahat = :id_istirahat
    """)
    with engine.begin() as conn:
        conn.execute(sql, {
            "id_istirahat": id_istirahat,
            "jam_selesai": jam_selesai,
            "durasi_menit": durasi_menit,
            "id_lokasi_balik": id_lokasi_balik,
            "now": get_wita()
        })

# HELPER HITUNG TOTAL MENIT ISTIRAHAT
def add_total_menit_istirahat(id_absensi: int, durasi_menit: int):
    sql = text("""
        UPDATE absensi
        SET total_menit_istirahat =
            COALESCE(total_menit_istirahat, 0) + :durasi,
            updated_at = :now
        WHERE id_absensi = :id_absensi
    """)
    with engine.begin() as conn:
        conn.execute(sql, {
            "id_absensi": id_absensi,
            "durasi": durasi_menit,
            "now": get_wita()
        })



# ====================================================
# ENDPOINT UNTUK KEPERLUAN MENU HISTORY
# ====================================================
def get_absensi_basic(id_pegawai: int, tanggal=None):
    """
    Ambil absensi basic:
    - Jika tanggal diisi → ambil absensi tanggal tsb
    - Jika tidak → ambil absensi aktif / terakhir
    """
    sql = text("""
        SELECT
            a.id_absensi, a.tanggal, a.jam_masuk, a.jam_keluar, a.menit_terlambat,
            lm.nama_lokasi AS lokasi_masuk,
            lk.nama_lokasi AS lokasi_keluar
        FROM absensi a
        LEFT JOIN ref_lokasi_absensi lm ON lm.id_lokasi = a.id_lokasi_masuk
        LEFT JOIN ref_lokasi_absensi lk ON lk.id_lokasi = a.id_lokasi_keluar
        WHERE a.id_pegawai = :id_pegawai
          AND a.status = 1
          AND (
                (:tanggal IS NOT NULL AND a.tanggal = :tanggal)
             OR (:tanggal IS NULL)
          )
        ORDER BY
            CASE
                WHEN a.jam_keluar IS NULL THEN 0
                ELSE 1
            END,
            a.tanggal DESC
        LIMIT 1
    """)
    with engine.connect() as conn:
        return conn.execute(
            sql,
            {
                "id_pegawai": id_pegawai,
                "tanggal": tanggal
            }
        ).mappings().first()


def get_pegawai_basic(id_pegawai: int):
    sql = text("""
        SELECT
            nama_lengkap, nama_panggilan
        FROM pegawai
        WHERE id_pegawai = :id_pegawai
          AND status = 1
        LIMIT 1
    """)
    with engine.connect() as conn:
        return conn.execute(
            sql, {"id_pegawai": id_pegawai}
        ).mappings().first()


def get_istirahat_absensi(id_absensi: int):
    sql = text("""
        SELECT
            ai.jam_mulai, ai.jam_selesai, ai.durasi_menit, lb.nama_lokasi AS lokasi_balik
        FROM absensi_istirahat ai
        LEFT JOIN ref_lokasi_absensi lb ON lb.id_lokasi = ai.id_lokasi_balik
        WHERE ai.id_absensi = :id_absensi
          AND ai.status = 1
        ORDER BY ai.jam_mulai ASC
    """)
    with engine.connect() as conn:
        return conn.execute(
            sql, {"id_absensi": id_absensi}
        ).mappings().all()
