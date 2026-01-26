from sqlalchemy import text
from api.utils.config import engine
from api.shared.helper import get_wita



# ======================================================================
# QUERY HELPER
# ======================================================================
def get_lembur_by_id(id_lembur: int):
    sql = text("""
        SELECT *
        FROM lembur
        WHERE id_lembur = :id
          AND status = 1
        LIMIT 1
    """)
    with engine.connect() as conn:
        return conn.execute(
            sql, {"id": id_lembur}
        ).mappings().first()



# ======================================================================
# QUERY PENGAJUAN LEMBUR OLEH PEGAWAI (PEGAWAI/LEMBURAN)
# ======================================================================
def insert_pengajuan_lembur(
    id_pegawai: int,
    id_jenis_lembur: int,
    tanggal,
    jam_mulai,
    jam_selesai,
    menit_lembur: int,
    keterangan: str,
    path_lampiran: str
):
    sql = text("""
        INSERT INTO lembur (
            id_pegawai, id_jenis_lembur, tanggal, jam_mulai, jam_selesai, menit_lembur, status_approval, 
            keterangan, path_lampiran, status
        )
        VALUES (
            :id_pegawai, :id_jenis_lembur, :tanggal, :jam_mulai, :jam_selesai, :menit_lembur, 'pending', 
            :keterangan, :path_lampiran, 1
        )
        RETURNING id_lembur
    """)
    with engine.begin() as conn:
        return conn.execute(
            sql,
            {
                "id_pegawai": id_pegawai,
                "id_jenis_lembur": id_jenis_lembur,
                "tanggal": tanggal,
                "jam_mulai": jam_mulai,
                "jam_selesai": jam_selesai,
                "menit_lembur": menit_lembur,
                "keterangan": keterangan,
                "path_lampiran": path_lampiran
            } ).scalar()


# ======================================================================
# QUERY LEMBURAN AKTIF OLEH PEGAWAI (PEGAWAI/LEMBURAN)
# ======================================================================
def get_lembur_aktif_harian(id_pegawai: int, tanggal):
    """
    Ambil lembur aktif pegawai di hari tertentu
    """
    sql = text("""
        SELECT
            l.id_lembur, l.id_jenis_lembur, jl.nama_jenis, l.tanggal, l.jam_mulai, l.jam_selesai, l.menit_lembur, 
            l.status_approval, l.keterangan
        FROM lembur l
        JOIN ref_jenis_lembur jl
            ON jl.id_jenis_lembur = l.id_jenis_lembur
        WHERE l.id_pegawai = :id_pegawai
          AND l.tanggal = :tanggal
          AND l.status = 1
          AND l.status_approval IN ('pending', 'approved')
        ORDER BY l.jam_mulai ASC
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
# QUERY HISTORY LEMBURAN OLEH PEGAWAI (PEGAWAI/LEMBURAN)
# ======================================================================
def get_history_lembur_bulanan(id_pegawai: int, bulan: int, tahun: int):
    """
    Ambil history lembur pegawai per bulan
    """
    sql = text("""
        SELECT
            l.id_lembur, l.id_jenis_lembur, jl.nama_jenis, l.tanggal, l.jam_mulai, l.jam_selesai, l.menit_lembur, 
            l.path_lampiran, l.total_bayaran, l.status_approval, l.keterangan, l.alasan_penolakan
        FROM lembur l
        JOIN ref_jenis_lembur jl
            ON jl.id_jenis_lembur = l.id_jenis_lembur
        WHERE l.id_pegawai = :id_pegawai
          AND EXTRACT(MONTH FROM l.tanggal) = :bulan
          AND EXTRACT(YEAR FROM l.tanggal) = :tahun
          AND l.status = 1
        ORDER BY l.tanggal DESC, l.jam_mulai DESC
    """)
    with engine.connect() as conn:
        return conn.execute(
            sql,
            {
                "id_pegawai": id_pegawai,
                "bulan": bulan,
                "tahun": tahun
            }
        ).mappings().all()


# ======================================================================
# QUERY DELETE LEMBUR OLEH PEGAWAI (PEGAWAI/LEMBURAN)
# ======================================================================
def soft_delete_lembur(id_lembur: int):
    sql = text("""
        UPDATE lembur
        SET
            status = 0,
            updated_at = :now
        WHERE id_lembur = :id
    """)
    with engine.begin() as conn:
        conn.execute(sql, {
            "id": id_lembur,
            "now": get_wita()
        })



# ======================================================================
# QUERY GET LIST LEMBUR BULANAN SEMUA PEGAWAI (ADMIN/LEMBURAN)
# ======================================================================
def get_lembur_list(
    start_date,
    end_date,
    status_approval=None,
    id_departemen=None,
    id_status_pegawai=None,
    id_pegawai=None
):
    sql = """
        SELECT
            l.id_lembur,
            l.id_pegawai,
            p.nama_panggilan,
            p.nip,

            d.nama_departemen,

            sp.id_status_pegawai,
            sp.nama_status AS status_pegawai,

            l.id_jenis_lembur,
            jl.nama_jenis,

            l.tanggal,
            l.jam_mulai,
            l.jam_selesai,
            l.menit_lembur,
            l.total_bayaran,
            l.status_approval,
            l.keterangan,
            l.path_lampiran,
            l.alasan_penolakan

        FROM lembur l
        JOIN pegawai p ON p.id_pegawai = l.id_pegawai
        LEFT JOIN ref_departemen d ON d.id_departemen = p.id_departemen
        LEFT JOIN ref_status_pegawai sp ON sp.id_status_pegawai = p.id_status_pegawai
        LEFT JOIN ref_jenis_lembur jl ON jl.id_jenis_lembur = l.id_jenis_lembur

        WHERE l.status = 1
          AND p.status = 1
          AND l.tanggal BETWEEN :start_date AND :end_date
    """

    params = {
        "start_date": start_date,
        "end_date": end_date
    }

    if status_approval:
        sql += " AND l.status_approval = :status_approval"
        params["status_approval"] = status_approval

    if id_departemen:
        sql += " AND p.id_departemen = :id_departemen"
        params["id_departemen"] = id_departemen

    if id_status_pegawai:
        sql += " AND p.id_status_pegawai = :id_status_pegawai"
        params["id_status_pegawai"] = id_status_pegawai

    if id_pegawai:
        sql += " AND l.id_pegawai = :id_pegawai"
        params["id_pegawai"] = id_pegawai

    sql += " ORDER BY l.tanggal DESC, l.created_at DESC"

    with engine.connect() as conn:
        return conn.execute(text(sql), params).mappings().all()



# ======================================================================
# QUERY UPDATE LEMBUR OLEH ADMIN (ADMIN/WEBBERKAH)
# ======================================================================
def update_lembur_admin(
    id_lembur: int,
    id_jenis_lembur: int,
    tanggal,
    jam_mulai,
    jam_selesai,
    menit_lembur: int,
    keterangan: str,
    path_lampiran: str | None
):
    sql = text("""
        UPDATE lembur
        SET
            id_jenis_lembur = :id_jenis_lembur,
            tanggal = :tanggal,
            jam_mulai = :jam_mulai,
            jam_selesai = :jam_selesai,
            menit_lembur = :menit_lembur,
            keterangan = :keterangan,
            path_lampiran = :path_lampiran,
            updated_at = :now
        WHERE id_lembur = :id_lembur
          AND status = 1
    """)

    with engine.begin() as conn:
        conn.execute(
            sql,
            {
                "id_lembur": id_lembur,
                "id_jenis_lembur": id_jenis_lembur,
                "tanggal": tanggal,
                "jam_mulai": jam_mulai,
                "jam_selesai": jam_selesai,
                "menit_lembur": menit_lembur,
                "keterangan": keterangan,
                "path_lampiran": path_lampiran,
                "now": get_wita()
            }
        )



# ======================================================================
# QUERY PEGAWAI PUNYA LEMBUR UNTUK FILTER NAMA (ADMIN/LEMBURAN)
# ======================================================================
def get_pegawai_with_lembur():
    """
    Ambil semua pegawai yang memiliki data lembur (status aktif)
    """

    sql = text("""
        SELECT DISTINCT
            p.id_pegawai,
            p.nip,
            p.nama_lengkap,
            p.nama_panggilan
        FROM lembur l
        JOIN pegawai p ON p.id_pegawai = l.id_pegawai
        WHERE l.status = 1
          AND p.status = 1
        ORDER BY p.nama_lengkap ASC
    """)

    with engine.connect() as conn:
        return conn.execute(sql).mappings().all()


# ======================================================================
# QUERY APPROVE/REJECT LEMBURAN PEGAWAI OLEH ADMIN (ADMIN/LEMBURAN)
# ======================================================================
def update_lembur_approval(
    id_lembur: int,
    status_approval: str,
    alasan_penolakan: str | None
):
    sql = text("""
        UPDATE lembur
        SET
            status_approval = :status_approval,
            alasan_penolakan = :alasan_penolakan,
            updated_at = :now
        WHERE id_lembur = :id
          AND status = 1
    """)

    with engine.begin() as conn:
        conn.execute(sql, {
            "id": id_lembur,
            "status_approval": status_approval,
            "alasan_penolakan": alasan_penolakan,
            "now": get_wita()
        })
