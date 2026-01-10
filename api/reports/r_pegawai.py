from sqlalchemy import text
from api.utils.config import engine


# ==================================================
# QUERIES REPORT UNTUK EXPORT PDF
# ==================================================
def get_pegawai_report_filtered(status_pegawai: str | None = None):
    sql = """
        SELECT
            p.id_pegawai, p.nip, p.nama_lengkap, p.nama_panggilan,
            p.jenis_kelamin, p.tanggal_masuk,

            d.nama_departemen,
            j.nama_jabatan,
            sp.nama_status AS status_pegawai,

            pr.no_telepon,
            pr.email_pribadi,
            pr.alamat

        FROM pegawai p
        LEFT JOIN ref_departemen d ON d.id_departemen = p.id_departemen
        LEFT JOIN ref_jabatan j ON j.id_jabatan = p.id_jabatan
        LEFT JOIN ref_status_pegawai sp ON sp.id_status_pegawai = p.id_status_pegawai
        LEFT JOIN pegawai_pribadi pr ON pr.id_pegawai = p.id_pegawai AND pr.status = 1

        WHERE p.status = 1
    """

    params = {}

    if status_pegawai:
        sql += " AND sp.nama_status = :status_pegawai"
        params["status_pegawai"] = status_pegawai

    sql += " ORDER BY p.tanggal_masuk ASC, p.id_pegawai ASC"

    with engine.connect() as conn:
        return conn.execute(text(sql), params).mappings().all()
    
    
    
def get_pegawai_rekening_report_filtered(status_pegawai: str | None = None):
    sql = """
        SELECT
            p.nip,
            p.nama_lengkap,
            p.tanggal_masuk,
            sp.nama_status AS status_pegawai,
            r.nama_bank,
            r.no_rekening,
            r.atas_nama
        FROM pegawai p
        LEFT JOIN ref_status_pegawai sp
            ON sp.id_status_pegawai = p.id_status_pegawai
        LEFT JOIN pegawai_rekening r
            ON r.id_pegawai = p.id_pegawai AND r.status = 1
        WHERE p.status = 1
    """

    params = {}

    if status_pegawai:
        sql += " AND sp.nama_status = :status_pegawai"
        params["status_pegawai"] = status_pegawai

    sql += " ORDER BY p.tanggal_masuk ASC, p.id_pegawai ASC"

    with engine.connect() as conn:
        return conn.execute(text(sql), params).mappings().all()



def get_pegawai_pendidikan_report_filtered(status_pegawai: str | None = None):
    sql = """
        SELECT
            p.nip,
            p.nama_lengkap,
            sp.nama_status AS status_pegawai,
            pp.jenjang,
            pp.institusi,
            pp.jurusan,
            pp.tahun_masuk,
            pp.tahun_lulus
        FROM pegawai p
        LEFT JOIN ref_status_pegawai sp
            ON sp.id_status_pegawai = p.id_status_pegawai
        LEFT JOIN pegawai_pendidikan pp
            ON pp.id_pegawai = p.id_pegawai AND pp.status = 1
        WHERE p.status = 1
    """

    params = {}

    if status_pegawai:
        sql += " AND sp.nama_status = :status_pegawai"
        params["status_pegawai"] = status_pegawai

    sql += " ORDER BY p.tanggal_masuk ASC, p.id_pegawai ASC"

    with engine.connect() as conn:
        return conn.execute(text(sql), params).mappings().all()



def get_pegawai_akun_report_filtered(status_pegawai: str | None = None):
    sql = """
        SELECT
            p.nip,
            p.nama_lengkap,
            p.tanggal_masuk,
            sp.nama_status AS status_pegawai,
            ap.username,
            ap.kode_pemulihan,
            ap.status AS auth_status
        FROM pegawai p
        LEFT JOIN ref_status_pegawai sp
            ON sp.id_status_pegawai = p.id_status_pegawai
        LEFT JOIN auth_pegawai ap
            ON ap.id_pegawai = p.id_pegawai AND ap.status IS NOT NULL
        WHERE p.status = 1
    """

    params = {}

    if status_pegawai:
        sql += " AND sp.nama_status = :status_pegawai"
        params["status_pegawai"] = status_pegawai

    sql += " ORDER BY p.tanggal_masuk ASC, p.id_pegawai ASC"

    with engine.connect() as conn:
        return conn.execute(text(sql), params).mappings().all()



def get_pegawai_lokasi_absensi_report_filtered(status_pegawai: str | None = None):
    """
    Ambil data lokasi absensi pegawai (1 pegawai bisa banyak lokasi)
    """
    sql = """
        SELECT
            p.id_pegawai,
            p.nip,
            p.nama_lengkap,
            p.tanggal_masuk,
            sp.nama_status AS status_pegawai,

            l.id_lokasi,
            l.nama_lokasi,
            l.latitude,
            l.longitude,
            l.radius_meter

        FROM pegawai p
        LEFT JOIN ref_status_pegawai sp
            ON sp.id_status_pegawai = p.id_status_pegawai
        LEFT JOIN pegawai_lokasi_absensi pla
            ON pla.id_pegawai = p.id_pegawai AND pla.status = 1
        LEFT JOIN ref_lokasi_absensi l
            ON l.id_lokasi = pla.id_lokasi AND l.status = 1

        WHERE p.status = 1
    """

    params = {}

    if status_pegawai:
        sql += " AND sp.nama_status = :status_pegawai"
        params["status_pegawai"] = status_pegawai

    sql += """
        ORDER BY
            p.tanggal_masuk,
            p.id_pegawai ASC,
            l.nama_lokasi ASC
    """

    with engine.connect() as conn:
        return conn.execute(text(sql), params).mappings().all()