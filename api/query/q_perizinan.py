from sqlalchemy import text
from api.utils.config import engine
from api.shared.helper import get_wita


# ======================================================================
# QUERY HELPER
# ======================================================================
def get_izin_by_id(id_izin: int):
    sql = text("""
        SELECT *
        FROM izin
        WHERE id_izin = :id
          AND status = 1
        LIMIT 1
    """)
    with engine.connect() as conn:
        return conn.execute(sql, {"id": id_izin}).mappings().first()
    


# ======================================================================
# QUERY PENGAJUAN IZIN OLEH PEGAWAI (PEGAWAI/WEBBERKAH)
# ======================================================================
def insert_pengajuan_izin(id_pegawai: int, id_jenis_izin: int, tgl_mulai, tgl_selesai, keterangan: str, path_lampiran: str | None):
    sql = text("""
        INSERT INTO izin (
            id_pegawai, id_jenis_izin, tgl_mulai, tgl_selesai, keterangan, path_lampiran, status_approval, 
            status, created_at, updated_at
        )
        VALUES (
            :id_pegawai, :id_jenis_izin, :tgl_mulai, :tgl_selesai, :keterangan, :path_lampiran, 'pending', 
            1, :now, :now
        )
        RETURNING id_izin
    """)
    with engine.begin() as conn:
        return conn.execute(
            sql,
            {
                "id_pegawai": id_pegawai,
                "id_jenis_izin": id_jenis_izin,
                "tgl_mulai": tgl_mulai,
                "tgl_selesai": tgl_selesai,
                "keterangan": keterangan,
                "path_lampiran": path_lampiran,
                "now": get_wita()
            }
        ).scalar()



# ======================================================================
# QUERY IZIN AKTIF OLEH PEGAWAI (PEGAWAI/WEBBERKAH)
# ======================================================================
def get_izin_aktif_harian(id_pegawai: int, tanggal):
    """
    Ambil izin aktif pegawai pada tanggal tertentu
    """
    sql = text("""
        SELECT
            i.id_izin, i.id_jenis_izin, ji.nama_izin, i.tgl_mulai, i.tgl_selesai, i.keterangan, i.path_lampiran, i.status_approval
        FROM izin i
        JOIN ref_jenis_izin ji
            ON ji.id_jenis_izin = i.id_jenis_izin
        WHERE i.id_pegawai = :id_pegawai
          AND i.status = 1
          AND i.status_approval IN ('pending', 'approved')
          AND :tanggal BETWEEN i.tgl_mulai AND i.tgl_selesai
        ORDER BY i.tgl_mulai ASC
    """)
    with engine.connect() as conn:
        return conn.execute(
            sql,
            {
                "id_pegawai": id_pegawai,
                "tanggal": tanggal
            }
        ).mappings().all()
    


# ======================================================================
# QUERY LIST IZIN PRIBADI OLEH PEGAWAI (PEGAWAI/WEBBERKAH)
# ======================================================================
def get_history_izin_bulanan(
    id_pegawai: int,
    start_date,
    end_date
):
    """
    Ambil history izin pegawai dalam rentang tanggal
    """
    sql = text("""
        SELECT
            i.id_izin, i.id_jenis_izin, ji.nama_izin, i.tgl_mulai, i.tgl_selesai, i.keterangan, 
            i.path_lampiran, i.status_approval, i.alasan_penolakan, i.created_at
        FROM izin i
        JOIN ref_jenis_izin ji
            ON ji.id_jenis_izin = i.id_jenis_izin
        WHERE i.id_pegawai = :id_pegawai
          AND i.status = 1
          AND i.tgl_mulai <= :end_date
          AND i.tgl_selesai >= :start_date
        ORDER BY i.created_at DESC
    """)
    with engine.connect() as conn:
        return conn.execute(
            sql,
            {
                "id_pegawai": id_pegawai,
                "start_date": start_date,
                "end_date": end_date
            }
        ).mappings().all()



# ======================================================================
# QUERY DELETE IZIN OLEH ADMIN & PEGAWAI 
# ======================================================================
def soft_delete_izin(id_izin: int):
    sql = text("""
        UPDATE izin
        SET
            status = 0,
            updated_at = :now
        WHERE id_izin = :id
    """)
    with engine.begin() as conn:
        conn.execute(sql, {
            "id": id_izin,
            "now": get_wita()
        })



# ======================================================================
# QUERY LIST IZIN OLEH ADMIN (ADMIN/WEBBERKAH)
# ======================================================================
def get_izin_list(
    start_date,
    end_date,
    status_approval=None,
    id_departemen=None,
    id_status_pegawai=None,
    id_pegawai=None,
    kategori_izin=None  # IZIN | SAKIT | CUTI
):
    sql = """
        SELECT
            i.id_izin,
            i.id_pegawai,
            p.nama_panggilan,
            p.nip,

            d.nama_departemen,

            sp.id_status_pegawai,
            sp.nama_status AS status_pegawai,

            i.id_jenis_izin,

            CASE
                WHEN i.id_jenis_izin = 3 THEN 'SAKIT'
                WHEN i.id_jenis_izin IN (1,2,4) THEN 'IZIN'
                WHEN i.id_jenis_izin IN (5,6) THEN 'CUTI'
                ELSE 'LAINNYA'
            END AS kategori_izin,

            i.tgl_mulai,
            i.tgl_selesai,
            (i.tgl_selesai - i.tgl_mulai + 1) AS durasi_izin,
            i.status_approval,
            i.keterangan,
            i.path_lampiran,
            i.alasan_penolakan

        FROM izin i
        JOIN pegawai p ON p.id_pegawai = i.id_pegawai
        LEFT JOIN ref_departemen d ON d.id_departemen = p.id_departemen
        LEFT JOIN ref_status_pegawai sp ON sp.id_status_pegawai = p.id_status_pegawai

        WHERE i.status = 1
          AND p.status = 1
          AND (
                i.tgl_mulai BETWEEN :start_date AND :end_date
                OR i.tgl_selesai BETWEEN :start_date AND :end_date
                OR :start_date BETWEEN i.tgl_mulai AND i.tgl_selesai
              )
    """

    params = {
        "start_date": start_date,
        "end_date": end_date
    }

    if status_approval:
        sql += " AND i.status_approval = :status_approval"
        params["status_approval"] = status_approval

    if id_departemen:
        sql += " AND p.id_departemen = :id_departemen"
        params["id_departemen"] = id_departemen

    if id_status_pegawai:
        sql += " AND p.id_status_pegawai = :id_status_pegawai"
        params["id_status_pegawai"] = id_status_pegawai

    if id_pegawai:
        sql += " AND i.id_pegawai = :id_pegawai"
        params["id_pegawai"] = id_pegawai

    if kategori_izin:
        if kategori_izin == "SAKIT":
            sql += " AND i.id_jenis_izin = 3"
        elif kategori_izin == "IZIN":
            sql += " AND i.id_jenis_izin IN (1,2,4)"
        elif kategori_izin == "CUTI":
            sql += " AND i.id_jenis_izin IN (5,6)"

    sql += " ORDER BY i.tgl_mulai DESC, i.created_at DESC"

    with engine.connect() as conn:
        return conn.execute(text(sql), params).mappings().all()



# ======================================================================
# QUERY UPDATE IZIN OLEH ADMIN (ADMIN/WEBBERKAH)
# ======================================================================
def update_izin_admin(
    id_izin: int,
    id_jenis_izin: int,
    tgl_mulai,
    tgl_selesai,
    keterangan: str,
    path_lampiran: str | None
):
    sql = text("""
        UPDATE izin
        SET
            id_jenis_izin = :id_jenis_izin,
            tgl_mulai = :tgl_mulai,
            tgl_selesai = :tgl_selesai,
            keterangan = :keterangan,
            path_lampiran = :path_lampiran,
            updated_at = :now
        WHERE id_izin = :id_izin
    """)

    with engine.begin() as conn:
        conn.execute(
            sql,
            {
                "id_izin": id_izin,
                "id_jenis_izin": id_jenis_izin,
                "tgl_mulai": tgl_mulai,
                "tgl_selesai": tgl_selesai,
                "keterangan": keterangan,
                "path_lampiran": path_lampiran,
                "now": get_wita()
            }
        )



# ======================================================================
# QUERY PEGAWAI PUNYA IZIN UNTUK FILTER NAMA (ADMIN/WEBBERKAH)
# ======================================================================
def get_pegawai_with_izin():
    """
    Ambil semua pegawai yang memiliki data izin (status aktif)
    """
    sql = text("""
        SELECT DISTINCT
            p.id_pegawai, p.nip, p.nama_lengkap, p.nama_panggilan
        FROM izin i
        JOIN pegawai p ON p.id_pegawai = i.id_pegawai
        WHERE i.status = 1
          AND p.status = 1
        ORDER BY p.nama_lengkap ASC
    """)
    with engine.connect() as conn:
        return conn.execute(sql).mappings().all()
    
    
# ======================================================================
# QUERY APPROVE/REJECT IZIN OLEH ADMIN (ADMIN/WEBBERKAH)
# ======================================================================
def update_izin_approval(
    id_izin: int,
    status_approval: str,
    alasan_penolakan: str | None
):
    sql = text("""
        UPDATE izin
        SET
            status_approval = :status_approval,
            alasan_penolakan = :alasan_penolakan,
            updated_at = :now
        WHERE id_izin = :id
          AND status = 1
    """)
    with engine.begin() as conn:
        conn.execute(sql, {
            "id": id_izin,
            "status_approval": status_approval,
            "alasan_penolakan": alasan_penolakan,
            "now": get_wita()
        })
