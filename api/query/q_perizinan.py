from sqlalchemy import text
from api.utils.config import engine
from api.shared.helper import get_wita



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



def get_izin_by_id(id_izin: int):
    sql = text("""
        SELECT
            id_izin,
            id_pegawai,
            status_approval,
            status
        FROM izin
        WHERE id_izin = :id
          AND status = 1
        LIMIT 1
    """)
    with engine.connect() as conn:
        return conn.execute(sql, {"id": id_izin}).mappings().first()


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
