from sqlalchemy import text
from api.utils.config import engine
from api.shared.helper import get_wita


# ==================================================
# REF STATUS PEGAWAI
# ==================================================
def get_status_pegawai_list():
    sql = text("""
        SELECT
            id_status_pegawai, nama_status, status, created_at, updated_at
        FROM ref_status_pegawai
        WHERE status = 1
        ORDER BY id_status_pegawai ASC
    """)
    with engine.connect() as conn:
        return conn.execute(sql).mappings().all()


def get_status_pegawai_by_id(id_status_pegawai: int):
    sql = text("""
        SELECT
            id_status_pegawai, nama_status, status, created_at, updated_at
        FROM ref_status_pegawai
        WHERE id_status_pegawai = :id
          AND status = 1
        LIMIT 1
    """)
    with engine.connect() as conn:
        return conn.execute(
            sql, {"id": id_status_pegawai}
        ).mappings().first()


def create_status_pegawai(nama_status: str):
    sql = text("""
        INSERT INTO ref_status_pegawai (nama_status)
        VALUES (:nama_status)
        RETURNING
            id_status_pegawai, nama_status, status, created_at, updated_at
    """)
    with engine.begin() as conn:
        return conn.execute(
            sql, {"nama_status": nama_status}
        ).mappings().first()


def update_status_pegawai(id_status_pegawai: int, nama_status: str):
    sql = text("""
        UPDATE ref_status_pegawai
        SET nama_status = :nama_status,
            updated_at = :now
        WHERE id_status_pegawai = :id
          AND status = 1
        RETURNING
            id_status_pegawai, nama_status, status, created_at, updated_at
    """)
    with engine.begin() as conn:
        return conn.execute(sql, {
            "id": id_status_pegawai,
            "nama_status": nama_status,
            "now": get_wita()
        }).mappings().first()


def delete_status_pegawai(id_status_pegawai: int):
    sql = text("""
        UPDATE ref_status_pegawai
        SET status = 0,
            updated_at = :now
        WHERE id_status_pegawai = :id
          AND status = 1
    """)
    with engine.begin() as conn:
        result = conn.execute(sql, {
            "id": id_status_pegawai,
            "now": get_wita()
        })
        return result.rowcount
    
    
    
# ==================================================
# REF DEPARTEMEN
# ==================================================
def get_departemen_list():
    sql = text("""
        SELECT
            id_departemen, nama_departemen, status, created_at, updated_at
        FROM ref_departemen
        WHERE status = 1
        ORDER BY id_departemen ASC
    """)
    with engine.connect() as conn:
        return conn.execute(sql).mappings().all()


def get_departemen_by_id(id_departemen: int):
    sql = text("""
        SELECT
            id_departemen, nama_departemen, status, created_at, updated_at
        FROM ref_departemen
        WHERE id_departemen = :id
          AND status = 1
        LIMIT 1
    """)
    with engine.connect() as conn:
        return conn.execute(
            sql, {"id": id_departemen}
        ).mappings().first()


def create_departemen(nama_departemen: str):
    sql = text("""
        INSERT INTO ref_departemen (nama_departemen)
        VALUES (:nama_departemen)
        RETURNING
            id_departemen, nama_departemen, status, created_at, updated_at
    """)
    with engine.begin() as conn:
        return conn.execute(
            sql, {"nama_departemen": nama_departemen}
        ).mappings().first()


def update_departemen(id_departemen: int, nama_departemen: str):
    sql = text("""
        UPDATE ref_departemen
        SET nama_departemen = :nama_departemen,
            updated_at = :now
        WHERE id_departemen = :id
          AND status = 1
        RETURNING
            id_departemen, nama_departemen, status, created_at, updated_at
    """)
    with engine.begin() as conn:
        return conn.execute(sql, {
            "id": id_departemen,
            "nama_departemen": nama_departemen,
            "now": get_wita()
        }).mappings().first()


def delete_departemen(id_departemen: int):
    sql = text("""
        UPDATE ref_departemen
        SET status = 0,
            updated_at = :now
        WHERE id_departemen = :id
          AND status = 1
    """)
    with engine.begin() as conn:
        result = conn.execute(sql, {
            "id": id_departemen,
            "now": get_wita()
        })
        return result.rowcount
    
    
    
# ==================================================
# REF JABATAN
# ==================================================
def get_jabatan_list():
    sql = text("""
        SELECT
            id_jabatan, nama_jabatan, status, created_at, updated_at
        FROM ref_jabatan
        WHERE status = 1
        ORDER BY id_jabatan ASC
    """)
    with engine.connect() as conn:
        return conn.execute(sql).mappings().all()


def get_jabatan_by_id(id_jabatan: int):
    sql = text("""
        SELECT
            id_jabatan, nama_jabatan, status, created_at, updated_at
        FROM ref_jabatan
        WHERE id_jabatan = :id
          AND status = 1
        LIMIT 1
    """)
    with engine.connect() as conn:
        return conn.execute(
            sql, {"id": id_jabatan}
        ).mappings().first()


def create_jabatan(nama_jabatan: str):
    sql = text("""
        INSERT INTO ref_jabatan (nama_jabatan)
        VALUES (:nama_jabatan)
        RETURNING
            id_jabatan, nama_jabatan, status, created_at, updated_at
    """)
    with engine.begin() as conn:
        return conn.execute(
            sql, {"nama_jabatan": nama_jabatan}
        ).mappings().first()


def update_jabatan(id_jabatan: int, nama_jabatan: str):
    sql = text("""
        UPDATE ref_jabatan
        SET nama_jabatan = :nama_jabatan,
            updated_at = :now
        WHERE id_jabatan = :id
          AND status = 1
        RETURNING
            id_jabatan, nama_jabatan, status, created_at, updated_at
    """)
    with engine.begin() as conn:
        return conn.execute(sql, {
            "id": id_jabatan,
            "nama_jabatan": nama_jabatan,
            "now": get_wita()
        }).mappings().first()


def delete_jabatan(id_jabatan: int):
    sql = text("""
        UPDATE ref_jabatan
        SET status = 0,
            updated_at = :now
        WHERE id_jabatan = :id
          AND status = 1
    """)
    with engine.begin() as conn:
        result = conn.execute(sql, {
            "id": id_jabatan,
            "now": get_wita()
        })
        return result.rowcount
    
    
    
# ==================================================
# REF LEVEL JABATAN
# ==================================================
def get_level_jabatan_list():
    sql = text("""
        SELECT
            id_level_jabatan, nama_level, urutan_level, status, created_at, updated_at
        FROM ref_level_jabatan
        WHERE status = 1
        ORDER BY urutan_level ASC
    """)
    with engine.connect() as conn:
        return conn.execute(sql).mappings().all()


def get_level_jabatan_by_id(id_level_jabatan: int):
    sql = text("""
        SELECT
            id_level_jabatan, nama_level, urutan_level, status, created_at, updated_at
        FROM ref_level_jabatan
        WHERE id_level_jabatan = :id
          AND status = 1
        LIMIT 1
    """)
    with engine.connect() as conn:
        return conn.execute(
            sql, {"id": id_level_jabatan}
        ).mappings().first()


def create_level_jabatan(nama_level: str, urutan_level: int):
    sql = text("""
        INSERT INTO ref_level_jabatan (nama_level, urutan_level)
        VALUES (:nama_level, :urutan_level)
        RETURNING
            id_level_jabatan, nama_level, urutan_level, status, created_at, updated_at
    """)
    with engine.begin() as conn:
        return conn.execute(sql, {
            "nama_level": nama_level,
            "urutan_level": urutan_level
        }).mappings().first()


def update_level_jabatan(id_level_jabatan: int, nama_level: str, urutan_level: int):
    sql = text("""
        UPDATE ref_level_jabatan
        SET nama_level = :nama_level,
            urutan_level = :urutan_level,
            updated_at = :now
        WHERE id_level_jabatan = :id
          AND status = 1
        RETURNING
            id_level_jabatan, nama_level, urutan_level, status, created_at, updated_at
    """)
    with engine.begin() as conn:
        return conn.execute(sql, {
            "id": id_level_jabatan,
            "nama_level": nama_level,
            "urutan_level": urutan_level,
            "now": get_wita()
        }).mappings().first()


def delete_level_jabatan(id_level_jabatan: int):
    sql = text("""
        UPDATE ref_level_jabatan
        SET status = 0,
            updated_at = :now
        WHERE id_level_jabatan = :id
          AND status = 1
    """)
    with engine.begin() as conn:
        result = conn.execute(sql, {
            "id": id_level_jabatan,
            "now": get_wita()
        })
        return result.rowcount
    
    
    
# ==================================================
# REF LEVEL JABATAN
# ==================================================
def get_jam_kerja_list():
    sql = text("""
        SELECT
            id_jam_kerja, nama_shift, jam_per_hari, status, created_at, updated_at
        FROM ref_jam_kerja
        WHERE status = 1
        ORDER BY id_jam_kerja ASC
    """)
    with engine.connect() as conn:
        return conn.execute(sql).mappings().all()


def get_jam_kerja_by_id(id_jam_kerja: int):
    sql = text("""
        SELECT
            id_jam_kerja, nama_shift, jam_per_hari, status, created_at, updated_at
        FROM ref_jam_kerja
        WHERE id_jam_kerja = :id
          AND status = 1
        LIMIT 1
    """)
    with engine.connect() as conn:
        return conn.execute(
            sql, {"id": id_jam_kerja}
        ).mappings().first()


def create_jam_kerja(nama_shift: str, jam_per_hari: int):
    sql = text("""
        INSERT INTO ref_jam_kerja (nama_shift, jam_per_hari)
        VALUES (:nama_shift, :jam_per_hari)
        RETURNING
            id_jam_kerja, nama_shift, jam_per_hari, status, created_at, updated_at
    """)
    with engine.begin() as conn:
        return conn.execute(sql, {
            "nama_shift": nama_shift,
            "jam_per_hari": jam_per_hari
        }).mappings().first()


def update_jam_kerja(id_jam_kerja: int, nama_shift: str, jam_per_hari: int):
    sql = text("""
        UPDATE ref_jam_kerja
        SET nama_shift = :nama_shift,
            jam_per_hari = :jam_per_hari,
            updated_at = :now
        WHERE id_jam_kerja = :id
          AND status = 1
        RETURNING
            id_jam_kerja, nama_shift, jam_per_hari, status, created_at, updated_at
    """)
    with engine.begin() as conn:
        return conn.execute(sql, {
            "id": id_jam_kerja,
            "nama_shift": nama_shift,
            "jam_per_hari": jam_per_hari,
            "now": get_wita()
        }).mappings().first()


def delete_jam_kerja(id_jam_kerja: int):
    sql = text("""
        UPDATE ref_jam_kerja
        SET status = 0,
            updated_at = :now
        WHERE id_jam_kerja = :id
          AND status = 1
    """)
    with engine.begin() as conn:
        result = conn.execute(sql, {
            "id": id_jam_kerja,
            "now": get_wita()
        })
        return result.rowcount



# ==================================================
# REF LOKASI ABSENSI
# ==================================================
def get_lokasi_absensi_list():
    sql = text("""
        SELECT
            id_lokasi, nama_lokasi, latitude, longitude, radius_meter, status, created_at, updated_at
        FROM ref_lokasi_absensi
        WHERE status = 1
        ORDER BY id_lokasi ASC
    """)
    with engine.connect() as conn:
        return conn.execute(sql).mappings().all()


def get_lokasi_absensi_by_id(id_lokasi: int):
    sql = text("""
        SELECT
            id_lokasi, nama_lokasi, latitude, longitude, radius_meter, status, created_at, updated_at
        FROM ref_lokasi_absensi
        WHERE id_lokasi = :id
          AND status = 1
        LIMIT 1
    """)
    with engine.connect() as conn:
        return conn.execute(
            sql, {"id": id_lokasi}
        ).mappings().first()


def create_lokasi_absensi(nama_lokasi: str, latitude: float, longitude: float, radius_meter: int):
    sql = text("""
        INSERT INTO ref_lokasi_absensi
            (nama_lokasi, latitude, longitude, radius_meter)
        VALUES
            (:nama_lokasi, :latitude, :longitude, :radius_meter)
        RETURNING
            id_lokasi, nama_lokasi, latitude, longitude, radius_meter, status, created_at, updated_at
    """)
    with engine.begin() as conn:
        return conn.execute(sql, {
            "nama_lokasi": nama_lokasi,
            "latitude": latitude,
            "longitude": longitude,
            "radius_meter": radius_meter
        }).mappings().first()


def update_lokasi_absensi(id_lokasi: int, nama_lokasi: str, latitude: float, longitude: float, radius_meter: int):
    sql = text("""
        UPDATE ref_lokasi_absensi
        SET nama_lokasi = :nama_lokasi,
            latitude = :latitude,
            longitude = :longitude,
            radius_meter = :radius_meter,
            updated_at = :now
        WHERE id_lokasi = :id
          AND status = 1
        RETURNING
            id_lokasi, nama_lokasi, latitude, longitude, radius_meter, status, created_at, updated_at
    """)
    with engine.begin() as conn:
        return conn.execute(sql, {
            "id": id_lokasi,
            "nama_lokasi": nama_lokasi,
            "latitude": latitude,
            "longitude": longitude,
            "radius_meter": radius_meter,
            "now": get_wita()
        }).mappings().first()


def delete_lokasi_absensi(id_lokasi: int):
    sql = text("""
        UPDATE ref_lokasi_absensi
        SET status = 0,
            updated_at = :now
        WHERE id_lokasi = :id
          AND status = 1
    """)
    with engine.begin() as conn:
        result = conn.execute(sql, {
            "id": id_lokasi,
            "now": get_wita()
        })
        return result.rowcount



# ==================================================
# REF JENIS IZIN
# ==================================================
def get_jenis_izin_list():
    sql = text("""
        SELECT
            id_jenis_izin, nama_izin, potong_cuti, status
        FROM ref_jenis_izin
        WHERE status = 1
        ORDER BY id_jenis_izin ASC
    """)
    with engine.connect() as conn:
        return conn.execute(sql).mappings().all()


def get_jenis_izin_by_id(id_jenis_izin: int):
    sql = text("""
        SELECT
            id_jenis_izin, nama_izin, potong_cuti, status
        FROM ref_jenis_izin
        WHERE id_jenis_izin = :id
          AND status = 1
        LIMIT 1
    """)
    with engine.connect() as conn:
        return conn.execute(
            sql, {"id": id_jenis_izin}
        ).mappings().first()


def create_jenis_izin(nama_izin: str, potong_cuti: bool):
    sql = text("""
        INSERT INTO ref_jenis_izin (nama_izin, potong_cuti)
        VALUES (:nama_izin, :potong_cuti)
        RETURNING
            id_jenis_izin, nama_izin, potong_cuti, status
    """)
    with engine.begin() as conn:
        return conn.execute(sql, {
            "nama_izin": nama_izin,
            "potong_cuti": potong_cuti
        }).mappings().first()


def update_jenis_izin(id_jenis_izin: int, nama_izin: str, potong_cuti: bool):
    sql = text("""
        UPDATE ref_jenis_izin
        SET nama_izin = :nama_izin,
            potong_cuti = :potong_cuti,
            status = 1
        WHERE id_jenis_izin = :id
          AND status = 1
        RETURNING
            id_jenis_izin, nama_izin, potong_cuti, status
    """)
    with engine.begin() as conn:
        return conn.execute(sql, {
            "id": id_jenis_izin,
            "nama_izin": nama_izin,
            "potong_cuti": potong_cuti
        }).mappings().first()


def delete_jenis_izin(id_jenis_izin: int):
    sql = text("""
        UPDATE ref_jenis_izin
        SET status = 0
        WHERE id_jenis_izin = :id
          AND status = 1
    """)
    with engine.begin() as conn:
        result = conn.execute(sql, {"id": id_jenis_izin})
        return result.rowcount



# ==================================================
# REF JENIS LEMBUR
# ==================================================
def get_jenis_lembur_list():
    sql = text("""
        SELECT
            id_jenis_lembur, nama_jenis, deskripsi, status
        FROM ref_jenis_lembur
        WHERE status = 1
        ORDER BY id_jenis_lembur ASC
    """)
    with engine.connect() as conn:
        return conn.execute(sql).mappings().all()


def get_jenis_lembur_by_id(id_jenis_lembur: int):
    sql = text("""
        SELECT
            id_jenis_lembur, nama_jenis, deskripsi, status
        FROM ref_jenis_lembur
        WHERE id_jenis_lembur = :id
          AND status = 1
        LIMIT 1
    """)
    with engine.connect() as conn:
        return conn.execute(
            sql, {"id": id_jenis_lembur}
        ).mappings().first()


def create_jenis_lembur(nama_jenis: str, deskripsi: str | None):
    sql = text("""
        INSERT INTO ref_jenis_lembur (nama_jenis, deskripsi)
        VALUES (:nama_jenis, :deskripsi)
        RETURNING
            id_jenis_lembur, nama_jenis, deskripsi, status
    """)
    with engine.begin() as conn:
        return conn.execute(sql, {
            "nama_jenis": nama_jenis,
            "deskripsi": deskripsi
        }).mappings().first()


def update_jenis_lembur(id_jenis_lembur: int, nama_jenis: str, deskripsi: str | None):
    sql = text("""
        UPDATE ref_jenis_lembur
        SET nama_jenis = :nama_jenis,
            deskripsi = :deskripsi,
            status = 1
        WHERE id_jenis_lembur = :id
          AND status = 1
        RETURNING
            id_jenis_lembur, nama_jenis, deskripsi, status
    """)
    with engine.begin() as conn:
        return conn.execute(sql, {
            "id": id_jenis_lembur,
            "nama_jenis": nama_jenis,
            "deskripsi": deskripsi
        }).mappings().first()


def delete_jenis_lembur(id_jenis_lembur: int):
    sql = text("""
        UPDATE ref_jenis_lembur
        SET status = 0
        WHERE id_jenis_lembur = :id
          AND status = 1
    """)
    with engine.begin() as conn:
        result = conn.execute(sql, {"id": id_jenis_lembur})
        return result.rowcount



# ==================================================
# REF LEMBUR RULE
# ==================================================
def get_lembur_rule_list():
    sql = text("""
        SELECT
            lr.id_rule, lr.id_jenis_lembur, jl.nama_jenis, lr.urutan_jam, lr.menit_dari, lr.menit_sampai, 
            lr.pengali, lr.status, lr.created_at, lr.updated_at
        FROM ref_lembur_rule lr
        JOIN ref_jenis_lembur jl
            ON jl.id_jenis_lembur = lr.id_jenis_lembur
        WHERE lr.status = 1
        ORDER BY lr.id_jenis_lembur, lr.urutan_jam ASC
    """)
    with engine.connect() as conn:
        return conn.execute(sql).mappings().all()


def get_lembur_rule_by_id(id_rule: int):
    sql = text("""
        SELECT
            lr.id_rule, lr.id_jenis_lembur, jl.nama_jenis, lr.urutan_jam, lr.menit_dari, lr.menit_sampai, 
            lr.pengali, lr.status, lr.created_at, lr.updated_at
        FROM ref_lembur_rule lr
        JOIN ref_jenis_lembur jl
            ON jl.id_jenis_lembur = lr.id_jenis_lembur
        WHERE lr.id_rule = :id
          AND lr.status = 1
        LIMIT 1
    """)
    with engine.connect() as conn:
        return conn.execute(
            sql, {"id": id_rule}
        ).mappings().first()


def create_lembur_rule(id_jenis_lembur: int, urutan_jam: int, menit_dari: int, menit_sampai: int, pengali: float):
    sql = text("""
        INSERT INTO ref_lembur_rule
            (id_jenis_lembur, urutan_jam, menit_dari, menit_sampai, pengali)
        VALUES
            (:id_jenis_lembur, :urutan_jam, :menit_dari, :menit_sampai, :pengali)
        RETURNING
            id_rule, id_jenis_lembur, urutan_jam, menit_dari, menit_sampai, pengali, status, created_at, updated_at
    """)
    with engine.begin() as conn:
        return conn.execute(sql, {
            "id_jenis_lembur": id_jenis_lembur,
            "urutan_jam": urutan_jam,
            "menit_dari": menit_dari,
            "menit_sampai": menit_sampai,
            "pengali": pengali
        }).mappings().first()


def update_lembur_rule(id_rule: int, id_jenis_lembur: int, urutan_jam: int, menit_dari: int, menit_sampai: int, pengali: float):
    sql = text("""
        UPDATE ref_lembur_rule
        SET id_jenis_lembur = :id_jenis_lembur,
            urutan_jam = :urutan_jam,
            menit_dari = :menit_dari,
            menit_sampai = :menit_sampai,
            pengali = :pengali,
            updated_at = :now
        WHERE id_rule = :id
          AND status = 1
        RETURNING
            id_rule, id_jenis_lembur, urutan_jam, menit_dari, menit_sampai, pengali, status, created_at, updated_at
    """)
    with engine.begin() as conn:
        return conn.execute(sql, {
            "id": id_rule,
            "id_jenis_lembur": id_jenis_lembur,
            "urutan_jam": urutan_jam,
            "menit_dari": menit_dari,
            "menit_sampai": menit_sampai,
            "pengali": pengali,
            "now": get_wita()
        }).mappings().first()


def delete_lembur_rule(id_rule: int):
    sql = text("""
        UPDATE ref_lembur_rule
        SET status = 0,
            updated_at = :now
        WHERE id_rule = :id
          AND status = 1
    """)
    with engine.begin() as conn:
        result = conn.execute(sql, {
            "id": id_rule,
            "now": get_wita()
        })
        return result.rowcount



# ==================================================
# REF HARI LIBUR
# ==================================================
def get_hari_libur_list():
    sql = text("""
        SELECT
            id_libur, tanggal, nama_libur, jenis, status, created_at, updated_at
        FROM ref_hari_libur
        WHERE status = 1
        ORDER BY tanggal ASC
    """)
    with engine.connect() as conn:
        return conn.execute(sql).mappings().all()


def get_hari_libur_by_id(id_libur: int):
    sql = text("""
        SELECT
            id_libur, tanggal, nama_libur, jenis, status, created_at, updated_at
        FROM ref_hari_libur
        WHERE id_libur = :id
          AND status = 1
        LIMIT 1
    """)
    with engine.connect() as conn:
        return conn.execute(
            sql, {"id": id_libur}
        ).mappings().first()


def create_hari_libur(tanggal, nama_libur: str, jenis: str):
    sql = text("""
        INSERT INTO ref_hari_libur (tanggal, nama_libur, jenis)
        VALUES (:tanggal, :nama_libur, :jenis)
        RETURNING
            id_libur, tanggal, nama_libur, jenis, status, created_at, updated_at
    """)
    with engine.begin() as conn:
        return conn.execute(sql, {
            "tanggal": tanggal,
            "nama_libur": nama_libur,
            "jenis": jenis
        }).mappings().first()


def update_hari_libur(id_libur: int, tanggal, nama_libur: str, jenis: str):
    sql = text("""
        UPDATE ref_hari_libur
        SET tanggal = :tanggal,
            nama_libur = :nama_libur,
            jenis = :jenis,
            updated_at = :now
        WHERE id_libur = :id
          AND status = 1
        RETURNING
            id_libur, tanggal, nama_libur, jenis, status, created_at, updated_at
    """)
    with engine.begin() as conn:
        return conn.execute(sql, {
            "id": id_libur,
            "tanggal": tanggal,
            "nama_libur": nama_libur,
            "jenis": jenis,
            "now": get_wita()
        }).mappings().first()


def delete_hari_libur(id_libur: int):
    sql = text("""
        UPDATE ref_hari_libur
        SET status = 0,
            updated_at = :now
        WHERE id_libur = :id
          AND status = 1
    """)
    with engine.begin() as conn:
        result = conn.execute(sql, {
            "id": id_libur,
            "now": get_wita()
        })
        return result.rowcount
