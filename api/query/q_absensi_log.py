import json
from sqlalchemy import text
from api.utils.config import engine
from api.shared.helper import get_wita


# ==================================================
# SIMPAN LOG ABSENSI
# ==================================================
def insert_absensi_log(
    id_pegawai: int, aksi: str, berhasil: bool, http_status: int,
    error_code=None, message=None, errors=None, latitude=None, longitude=None,
    id_absensi=None, id_jam_kerja=None, durasi_ms=None, detail_teknis=None
):
    sql = text("""
        INSERT INTO absensi_log (
            id_pegawai, aksi, berhasil, http_status, error_code, message, errors,
            latitude, longitude, id_absensi, id_jam_kerja, durasi_ms, detail_teknis, created_at
        )
        VALUES (
            :id_pegawai, :aksi, :berhasil, :http_status, :error_code, :message, CAST(:errors AS JSONB),
            :latitude, :longitude, :id_absensi, :id_jam_kerja, :durasi_ms, :detail_teknis, :now
        )
    """)
    with engine.begin() as conn:
        conn.execute(sql, {
            "id_pegawai": id_pegawai,
            "aksi": aksi,
            "berhasil": berhasil,
            "http_status": http_status,
            "error_code": error_code,
            "message": message,
            "errors": json.dumps(errors, default=str) if errors is not None else None,
            "latitude": latitude,
            "longitude": longitude,
            "id_absensi": id_absensi,
            "id_jam_kerja": id_jam_kerja,
            "durasi_ms": durasi_ms,
            "detail_teknis": detail_teknis,
            "now": get_wita()
        })


# ==================================================
# FILTER LOG (DIPAKAI LIST & RINGKASAN)
# ==================================================
def _build_filter_log(filters: dict):
    where = ["1 = 1"]
    params = {}

    if filters.get("id_pegawai"):
        where.append("l.id_pegawai = :id_pegawai")
        params["id_pegawai"] = filters["id_pegawai"]

    if filters.get("id_departemen"):
        where.append("p.id_departemen = :id_departemen")
        params["id_departemen"] = filters["id_departemen"]

    if filters.get("aksi"):
        where.append("l.aksi = :aksi")
        params["aksi"] = filters["aksi"]

    if filters.get("error_code"):
        where.append("l.error_code = :error_code")
        params["error_code"] = filters["error_code"]

    if filters.get("http_status"):
        where.append("l.http_status = :http_status")
        params["http_status"] = filters["http_status"]

    if filters.get("berhasil") is not None:
        where.append("l.berhasil = :berhasil")
        params["berhasil"] = filters["berhasil"]

    if filters.get("tanggal_mulai"):
        where.append("l.created_at >= :tanggal_mulai")
        params["tanggal_mulai"] = filters["tanggal_mulai"]

    if filters.get("tanggal_selesai"):
        # inklusif sampai akhir hari tanggal_selesai
        where.append("l.created_at < CAST(:tanggal_selesai AS DATE) + INTERVAL '1 day'")
        params["tanggal_selesai"] = filters["tanggal_selesai"]

    if filters.get("search"):
        where.append("(p.nama_lengkap ILIKE :search OR p.nip ILIKE :search OR l.message ILIKE :search)")
        params["search"] = f"%{filters['search']}%"

    return " AND ".join(where), params


# ==================================================
# LIST LOG UNTUK ADMIN (PAGINASI)
# ==================================================
def get_absensi_log_list(filters: dict, page: int, limit: int):
    where_sql, params = _build_filter_log(filters)

    sql_data = text(f"""
        SELECT
            l.id_log, l.created_at, l.aksi, l.berhasil, l.http_status, l.error_code,
            l.message, l.errors, l.latitude, l.longitude, l.id_absensi, l.id_jam_kerja,
            l.durasi_ms, (l.detail_teknis IS NOT NULL) AS ada_detail_teknis,
            p.id_pegawai, p.nip, p.nama_lengkap, p.nama_panggilan,
            d.id_departemen, d.nama_departemen
        FROM absensi_log l
        JOIN pegawai p ON p.id_pegawai = l.id_pegawai
        LEFT JOIN ref_departemen d ON d.id_departemen = p.id_departemen
        WHERE {where_sql}
        ORDER BY l.created_at DESC, l.id_log DESC
        LIMIT :limit OFFSET :offset
    """)
    sql_total = text(f"""
        SELECT COUNT(*)
        FROM absensi_log l
        JOIN pegawai p ON p.id_pegawai = l.id_pegawai
        WHERE {where_sql}
    """)

    with engine.connect() as conn:
        total = conn.execute(sql_total, params).scalar()
        rows = conn.execute(sql_data, {
            **params, "limit": limit, "offset": (page - 1) * limit
        }).mappings().all()

    return rows, total


# ==================================================
# DETAIL LOG (TERMASUK DETAIL TEKNIS / TRACEBACK)
# ==================================================
def get_absensi_log_by_id(id_log: int):
    sql = text("""
        SELECT
            l.*, p.nip, p.nama_lengkap, p.nama_panggilan,
            d.id_departemen, d.nama_departemen
        FROM absensi_log l
        JOIN pegawai p ON p.id_pegawai = l.id_pegawai
        LEFT JOIN ref_departemen d ON d.id_departemen = p.id_departemen
        WHERE l.id_log = :id_log
    """)
    with engine.connect() as conn:
        return conn.execute(sql, {"id_log": id_log}).mappings().first()


# ==================================================
# RINGKASAN LOG: JUMLAH PER ERROR_CODE & PER AKSI
# ==================================================
def get_absensi_log_ringkasan(filters: dict):
    where_sql, params = _build_filter_log(filters)
    base = f"""
        FROM absensi_log l
        JOIN pegawai p ON p.id_pegawai = l.id_pegawai
        WHERE {where_sql}
    """
    sql_per_error = text(f"""
        SELECT l.error_code, l.http_status, COUNT(*) AS jumlah,
               COUNT(DISTINCT l.id_pegawai) AS jumlah_pegawai,
               MAX(l.created_at) AS terakhir
        {base}
        GROUP BY l.error_code, l.http_status
        ORDER BY jumlah DESC
    """)
    sql_per_aksi = text(f"""
        SELECT l.aksi, COUNT(*) AS jumlah
        {base}
        GROUP BY l.aksi
        ORDER BY jumlah DESC
    """)
    sql_per_pegawai = text(f"""
        SELECT p.id_pegawai, p.nama_lengkap, COUNT(*) AS jumlah
        {base}
        GROUP BY p.id_pegawai, p.nama_lengkap
        ORDER BY jumlah DESC
        LIMIT 10
    """)
    with engine.connect() as conn:
        return {
            "per_error_code": conn.execute(sql_per_error, params).mappings().all(),
            "per_aksi": conn.execute(sql_per_aksi, params).mappings().all(),
            "top_pegawai": conn.execute(sql_per_pegawai, params).mappings().all(),
        }
