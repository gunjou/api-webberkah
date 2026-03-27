from sqlalchemy import text
from api.utils.config import engine
from api.shared.helper import get_wita


def get_leaderboard_terlambat(start_date, end_date, limit=10):
    sql = text("""
        SELECT
            p.id_pegawai,
            p.nama_lengkap,
            p.nama_panggilan,
            p.nip,
            d.nama_departemen,
            s.nama_status,
            COALESCE(SUM(a.menit_terlambat), 0) AS total_menit_terlambat
        FROM pegawai p
        LEFT JOIN absensi a
            ON a.id_pegawai = p.id_pegawai
            AND a.status = 1
            AND a.tanggal BETWEEN :start AND :end
        LEFT JOIN ref_departemen d
            ON d.id_departemen = p.id_departemen
        LEFT JOIN ref_status_pegawai s
            ON s.id_status_pegawai = p.id_status_pegawai
        WHERE p.status = 1
        GROUP BY 
            p.id_pegawai, p.nama_lengkap, p.nama_panggilan, p.nip,
            d.nama_departemen, s.nama_status
        HAVING COALESCE(SUM(a.menit_terlambat), 0) > 0
        ORDER BY total_menit_terlambat DESC
        LIMIT :limit
    """)

    with engine.connect() as conn:
        rows = conn.execute(sql, {
            "start": start_date,
            "end": end_date,
            "limit": limit
        }).mappings().all()

    return rows