from sqlalchemy import text
from api.utils.config import engine
from api.shared.helper import get_wita



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


def get_lembur_by_id(id_lembur: int):
    sql = text("""
        SELECT
            id_lembur,
            id_pegawai,
            status_approval,
            status
        FROM lembur
        WHERE id_lembur = :id
          AND status = 1
        LIMIT 1
    """)
    with engine.connect() as conn:
        return conn.execute(sql, {"id": id_lembur}).mappings().first()


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
