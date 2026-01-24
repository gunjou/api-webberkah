# api/query/q_dashboard.py
from sqlalchemy import text
from api.utils.config import engine
from api.shared.helper import get_wita



# ======================================================================
# QUERY COUNT TOTAL NOTIFIKASI DI LONCENG NAVBAR (ADMIN/WEBBERKAH)
# ======================================================================
def get_dashboard_notifikasi_count():
    """
    Hitung notifikasi dashboard:
    - izin pending
    - lembur pending
    """
    sql = text("""
        SELECT
            -- izin pending
            (
                SELECT COUNT(*)
                FROM izin
                WHERE status = 1
                  AND status_approval = 'pending'
            ) AS izin_pending,

            -- lembur pending
            (
                SELECT COUNT(*)
                FROM lembur
                WHERE status = 1
                  AND status_approval = 'pending'
            ) AS lembur_pending
    """)

    with engine.connect() as conn:
        return conn.execute(sql).mappings().first()
    

# ======================================================================
# QUERY COUNT TOTAL PEGAWAI AKTIF CARD DASHBOARD (ADMIN/WEBBERKAH)
# ======================================================================
def count_pegawai_aktif_dashboard():
    """
    Hitung jumlah pegawai aktif
    (exclude pegawai tertentu)
    """
    sql = text("""
        SELECT COUNT(*) AS total
        FROM pegawai
        WHERE status = 1
          AND id_pegawai NOT IN (2, 13)
    """)

    with engine.connect() as conn:
        return conn.execute(sql).scalar()


# ======================================================================
# QUERY LIST PEGAWAI AKTIF SECARA UMUM (ADMIN/WEBBERKAH)
# ======================================================================
def get_pegawai_aktif_dashboard():
    """
    Ambil data pegawai aktif untuk dashboard
    (exclude direktur & staf ahli)
    """
    sql = text("""
        SELECT
            p.id_pegawai, p.nip, p.nama_lengkap, p.nama_panggilan, d.id_departemen, d.nama_departemen, 
            sp.id_status_pegawai, sp.nama_status AS status_pegawai
        FROM pegawai p
        LEFT JOIN ref_departemen d
               ON d.id_departemen = p.id_departemen
              AND d.status = 1
        LEFT JOIN ref_status_pegawai sp
               ON sp.id_status_pegawai = p.id_status_pegawai
              AND sp.status = 1
        WHERE p.status = 1
          AND p.id_pegawai NOT IN (2, 13)
        ORDER BY p.nama_lengkap ASC
    """)

    with engine.connect() as conn:
        rows = conn.execute(sql).mappings().all()

    return rows


# ======================================================================
# QUERY LIST PEGAWAI HADIR HARI INI DI DASHBOARD (ADMIN/WEBBERKAH)
# ======================================================================
def get_presensi_hadir_hari_ini_simple():
    """
    Data pegawai yang hadir hari ini
    (query ringan, tanpa view)
    """
    today = get_wita().date()

    sql = text("""
        SELECT
            a.id_absensi, a.tanggal, a.jam_masuk   AS jam_checkin, a.jam_keluar  AS jam_checkout, a.menit_terlambat,

            p.id_pegawai, p.nip, p.nama_lengkap, p.nama_panggilan,

            d.id_departemen, d.nama_departemen,

            sp.id_status_pegawai, sp.nama_status AS status_pegawai

        FROM absensi a
        JOIN pegawai p
          ON p.id_pegawai = a.id_pegawai
         AND p.status = 1

        LEFT JOIN ref_departemen d
          ON d.id_departemen = p.id_departemen
         AND d.status = 1

        LEFT JOIN ref_status_pegawai sp
          ON sp.id_status_pegawai = p.id_status_pegawai
         AND sp.status = 1

        WHERE a.tanggal = :tanggal
          AND a.jam_masuk IS NOT NULL
          AND a.status = 1
          AND p.id_pegawai NOT IN (2, 13)

        ORDER BY a.jam_masuk ASC
    """)

    with engine.connect() as conn:
        rows = conn.execute(sql, {
            "tanggal": today
        }).mappings().all()

    return rows


# ======================================================================
# QUERY LIST PEGAWAI TERLAMBAT HARI INI DI DASHBOARD (ADMIN/WEBBERKAH)
# ======================================================================
def get_presensi_terlambat_hari_ini_simple():
    """
    Data pegawai yang terlambat hari ini
    (query ringan, tanpa view besar)
    """
    today = get_wita().date()

    sql = text("""
        SELECT
            a.id_absensi, a.tanggal, a.jam_masuk AS jam_checkin, a.menit_terlambat,
            p.id_pegawai, p.nip, p.nama_lengkap, p.nama_panggilan,
            d.nama_departemen, sp.nama_status AS status_pegawai
        FROM absensi a
        JOIN pegawai p ON p.id_pegawai = a.id_pegawai AND p.status = 1
        LEFT JOIN ref_departemen d ON d.id_departemen = p.id_departemen AND d.status = 1
        LEFT JOIN ref_status_pegawai sp ON sp.id_status_pegawai = p.id_status_pegawai AND sp.status = 1
        WHERE a.tanggal = :tanggal
          AND a.menit_terlambat > 0
          AND a.status = 1
          AND p.id_pegawai NOT IN (2, 13)
        ORDER BY a.menit_terlambat DESC, a.jam_masuk ASC
    """)
    with engine.connect() as conn:
        rows = conn.execute(sql, {
            "tanggal": today
        }).mappings().all()

    return rows


# ======================================================================
# QUERY LIST PEGAWAI IZIN HARI INI DI DASHBOARD (ADMIN/WEBBERKAH)
# ======================================================================
def get_pegawai_izin_hari_ini_dashboard():
    """
    Data pegawai izin / sakit / cuti hari ini
    (digabung dalam satu endpoint dashboard)
    """
    today = get_wita().date()

    sql = text("""
        SELECT
            p.id_pegawai, p.nip, p.nama_lengkap, p.nama_panggilan,

            d.id_departemen, d.nama_departemen,

            sp.id_status_pegawai, sp.nama_status AS status_pegawai,

            i.id_izin, i.id_jenis_izin, i.tgl_mulai, i.tgl_selesai, i.keterangan,

            CASE
                WHEN i.id_jenis_izin = 3 THEN 'SAKIT'
                WHEN i.id_jenis_izin IN (1, 2, 6) THEN 'IZIN'
                WHEN i.id_jenis_izin IN (4, 5) THEN 'CUTI'
                ELSE 'LAINNYA'
            END AS kategori_izin

        FROM izin i
        JOIN pegawai p
          ON p.id_pegawai = i.id_pegawai
         AND p.status = 1

        LEFT JOIN ref_departemen d
          ON d.id_departemen = p.id_departemen
         AND d.status = 1

        LEFT JOIN ref_status_pegawai sp
          ON sp.id_status_pegawai = p.id_status_pegawai
         AND sp.status = 1

        WHERE i.status = 1
          AND i.status_approval = 'approved'
          AND :tanggal BETWEEN i.tgl_mulai AND i.tgl_selesai
          AND i.id_jenis_izin IN (1, 2, 3, 4, 5, 6)
          AND p.id_pegawai NOT IN (2, 13)

        ORDER BY kategori_izin, p.nama_lengkap ASC
    """)

    with engine.connect() as conn:
        rows = conn.execute(sql, {
            "tanggal": today
        }).mappings().all()

    return rows


# ======================================================================
# QUERY LIST PEGAWAI ALPHA HARI INI DI DASHBOARD (ADMIN/WEBBERKAH)
# ======================================================================
def get_pegawai_alpha_hari_ini():
    """
    Pegawai ALPHA hari ini:
    - aktif
    - tidak absen
    - tidak izin
    - exclude pegawai tertentu
    """
    today = get_wita().date()

    sql = text("""
        SELECT
            p.id_pegawai, p.nip, p.nama_lengkap, p.nama_panggilan,

            d.id_departemen, d.nama_departemen,

            sp.id_status_pegawai, sp.nama_status AS status_pegawai

        FROM pegawai p

        LEFT JOIN ref_departemen d
               ON d.id_departemen = p.id_departemen
              AND d.status = 1

        LEFT JOIN ref_status_pegawai sp
               ON sp.id_status_pegawai = p.id_status_pegawai
              AND sp.status = 1

        -- cek absensi hari ini
        LEFT JOIN absensi a
               ON a.id_pegawai = p.id_pegawai
              AND a.tanggal = :tanggal
              AND a.status = 1

        -- cek izin yang mencakup hari ini
        LEFT JOIN izin i
               ON i.id_pegawai = p.id_pegawai
              AND i.status = 1
              AND i.status_approval = 'approved'
              AND :tanggal BETWEEN i.tgl_mulai AND i.tgl_selesai

        WHERE p.status = 1
          AND p.id_pegawai NOT IN (2, 13)
          AND a.id_absensi IS NULL
          AND i.id_izin IS NULL

        ORDER BY p.nama_lengkap ASC
    """)

    with engine.connect() as conn:
        rows = conn.execute(sql, {
            "tanggal": today
        }).mappings().all()

    return rows


# ======================================================================
# QUERY LIST SEBARAN LOKASI ABSENSI DI DASHBOARD (ADMIN/WEBBERKAH)
# ======================================================================
def get_sebaran_presensi_lokasi_hari_ini():
    """
    Sebaran pegawai hadir hari ini per lokasi absensi
    (untuk dashboard admin)
    """
    today = get_wita().date()

    sql = text("""
        SELECT
            id_lokasi_masuk AS id_lokasi, lokasi_checkin AS nama_lokasi, COUNT(*) AS total
        FROM v_admin_presensi_harian
        WHERE tanggal = :tanggal
          AND jam_checkin IS NOT NULL
          AND id_pegawai NOT IN (2, 13)
        GROUP BY id_lokasi_masuk, lokasi_checkin
        ORDER BY total DESC
    """)
    with engine.connect() as conn:
        rows = conn.execute(sql, {
            "tanggal": today
        }).mappings().all()
    return rows