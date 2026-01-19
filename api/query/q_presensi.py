from datetime import timedelta
from sqlalchemy import text
from api.utils.config import engine
from api.shared.helper import get_wita


# ======================================================================
# HELPER PRESENSI HARIAN SEMUA PEGAWAI (ADMIN.WEBBERKAH)
# ======================================================================
def hitung_durasi_menit(jam_mulai, jam_selesai):
    if not jam_mulai or not jam_selesai:
        return 0

    mulai = jam_mulai.hour * 60 + jam_mulai.minute
    selesai = jam_selesai.hour * 60 + jam_selesai.minute

    # shift lintas hari
    if selesai < mulai:
        selesai += 24 * 60

    return max(0, selesai - mulai)



# ======================================================================
# QUERY GET DATA PRESENSI HARIAN SEMUA PEGAWAI (ADMIN.WEBBERKAH)
# ======================================================================
def get_admin_presensi_harian(tanggal, id_departemen=None, id_status_pegawai=None):
    """
    Ambil data presensi admin (pakai VIEW)
    """

    sql = """
        SELECT *
        FROM v_admin_presensi_harian
        WHERE tanggal = :tanggal
    """

    params = {"tanggal": tanggal}

    if id_departemen:
        sql += " AND id_departemen = :id_departemen"
        params["id_departemen"] = id_departemen

    if id_status_pegawai:
        sql += " AND id_status_pegawai = :id_status_pegawai"
        params["id_status_pegawai"] = id_status_pegawai

    sql += " ORDER BY jam_checkin DESC NULLS LAST"

    with engine.connect() as conn:
        return conn.execute(
            text(sql),
            params
        ).mappings().all()


# ======================================================================
# QUERY UPDATE PRESENSI PEGAWAI BY ID (ADMIN.WEBBERKAH)
# ======================================================================
# GET DATA
def get_absensi_by_id(id_absensi):
    sql = text("""
        SELECT a.*, jk.jam_mulai
        FROM absensi a
        JOIN ref_jam_kerja jk ON jk.id_jam_kerja = a.id_jam_kerja
        WHERE a.id_absensi = :id
          AND a.status = 1
        LIMIT 1
    """)
    with engine.connect() as conn:
        return conn.execute(sql, {"id": id_absensi}).mappings().first()


# UPDATE ABSENSI
def update_absensi_manual(id_absensi: int, jam_masuk=None, jam_keluar=None, id_lokasi_masuk=None, id_lokasi_keluar=None):
    fields = []
    params = {
        "id": id_absensi,
        "now": get_wita()
    }

    def add(field, value):
        fields.append(f"{field} = :{field}")
        params[field] = value

    # ⬇️ LANGSUNG TAMBAHKAN, TANPA CEK
    add("jam_masuk", jam_masuk)
    add("jam_keluar", jam_keluar)
    add("id_lokasi_masuk", id_lokasi_masuk)
    add("id_lokasi_keluar", id_lokasi_keluar)

    sql = f"""
        UPDATE absensi
        SET {', '.join(fields)},
            updated_at = :now
        WHERE id_absensi = :id
    """

    with engine.begin() as conn:
        conn.execute(text(sql), params)


# ISTIRAHAT UPSERT
def upsert_absensi_istirahat(id_absensi: int, jam_mulai=None, jam_selesai=None, id_lokasi_balik=None):
    istirahat = get_active_istirahat(id_absensi)
    durasi_menit = hitung_durasi_menit(jam_mulai, jam_selesai)

    params = {
        "id_absensi": id_absensi,
        "jam_mulai": jam_mulai,
        "jam_selesai": jam_selesai,
        "id_lokasi_balik": id_lokasi_balik,
        "durasi_menit": durasi_menit,
        "now": get_wita()
    }

    if istirahat:
        sql = text("""
            UPDATE absensi_istirahat
            SET
                jam_mulai = :jam_mulai,
                jam_selesai = :jam_selesai,
                id_lokasi_balik = :id_lokasi_balik,
                durasi_menit = :durasi_menit,
                updated_at = :now
            WHERE id_istirahat = :id
        """)
        params["id"] = istirahat["id_istirahat"]
    else:
        sql = text("""
            INSERT INTO absensi_istirahat (
                id_absensi, jam_mulai, jam_selesai, id_lokasi_balik, durasi_menit, status, created_at, updated_at
            ) VALUES (
                :id_absensi, :jam_mulai, :jam_selesai, :id_lokasi_balik, :durasi_menit, 1, :now, :now
            )
        """)
    with engine.begin() as conn:
        conn.execute(sql, params) 


def get_active_istirahat(id_absensi):
    sql = text("""
        SELECT *
        FROM absensi_istirahat
        WHERE id_absensi = :id
          AND status = 1
        LIMIT 1
    """)
    with engine.connect() as conn:
        return conn.execute(sql, {"id": id_absensi}).mappings().first()


# RECALCULATION
def recalc_absensi(id_absensi):
    absensi = get_absensi_by_id(id_absensi)
    if not absensi:
        return

    total_istirahat = hitung_total_istirahat(id_absensi)
    menit_terlambat = hitung_menit_terlambat(
        absensi["jam_masuk"],
        absensi["jam_mulai"]
    )

    total_kerja = None
    if absensi["jam_masuk"] and absensi["jam_keluar"]:
        total_kerja = hitung_total_menit_kerja(
            absensi["jam_masuk"],
            absensi["jam_keluar"],
            total_istirahat
        )

    sql = text("""
        UPDATE absensi
        SET
            total_menit_istirahat = :istirahat,
            menit_terlambat = :terlambat,
            total_menit_kerja = :kerja,
            updated_at = :now
        WHERE id_absensi = :id
    """)

    with engine.begin() as conn:
        conn.execute(sql, {
            "id": id_absensi,
            "istirahat": total_istirahat,
            "terlambat": menit_terlambat,
            "kerja": total_kerja,
            "now": get_wita()
        })


# HELPER HITUNG
def hitung_total_istirahat(id_absensi):
    sql = text("""
        SELECT COALESCE(SUM(durasi_menit), 0)
        FROM absensi_istirahat
        WHERE id_absensi = :id
          AND status = 1
          AND jam_mulai IS NOT NULL
          AND jam_selesai IS NOT NULL
    """)
    with engine.connect() as conn:
        return conn.execute(sql, {"id": id_absensi}).scalar()

def hitung_menit_terlambat(jam_masuk, jam_mulai):
    if not jam_masuk or not jam_mulai:
        return 0
    masuk = jam_masuk.hour * 60 + jam_masuk.minute
    mulai = jam_mulai.hour * 60 + jam_mulai.minute
    return max(0, masuk - mulai)

def hitung_total_menit_kerja(jam_masuk, jam_keluar, menit_istirahat):
    masuk = jam_masuk.hour * 60 + jam_masuk.minute
    keluar = jam_keluar.hour * 60 + jam_keluar.minute
    if keluar < masuk:  # shift malam
        keluar += 24 * 60
    return max(0, keluar - masuk - (menit_istirahat or 0))



# ======================================================================
# QUERY DELETE PRESENSI PEGAWAI BY ID (ADMIN.WEBBERKAH)
# ======================================================================
def soft_delete_presensi(id_absensi: int):
    sql = text("""
        UPDATE absensi
        SET
            status = 0,
            updated_at = :now
        WHERE id_absensi = :id
    """)

    with engine.begin() as conn:
        conn.execute(sql, {
            "id": id_absensi,
            "now": get_wita()
        })



# ======================================================================
# QUERY ADD PRESENSI MANUAL PEGAWAI BY ID OLEH ADMIN (ADMIN.WEBBERKAH)
# ======================================================================
def is_pegawai_active(id_pegawai):
    sql = text("""
        SELECT 1 FROM pegawai
        WHERE id_pegawai = :id AND status = 1
    """)
    with engine.connect() as conn:
        return conn.execute(sql, {"id": id_pegawai}).first() is not None

def is_absensi_exist(id_pegawai, tanggal):
    sql = text("""
        SELECT 1 FROM absensi
        WHERE id_pegawai = :id
          AND tanggal = :tanggal
          AND status = 1
    """)
    with engine.connect() as conn:
        return conn.execute(sql, {
            "id": id_pegawai,
            "tanggal": tanggal
        }).first() is not None

def insert_absensi_manual(
    id_pegawai,
    tanggal,
    id_jam_kerja,
    jam_masuk,
    jam_keluar,
    id_lokasi_masuk,
    id_lokasi_keluar,
    menit_terlambat
):
    sql = text("""
        INSERT INTO absensi (
            id_pegawai, tanggal, id_jam_kerja, jam_masuk, jam_keluar, id_lokasi_masuk, id_lokasi_keluar, 
            menit_terlambat, status, created_at, updated_at
        ) VALUES (
            :id_pegawai, :tanggal, :id_jam_kerja, :jam_masuk, :jam_keluar, :id_lokasi_masuk, :id_lokasi_keluar, 
            :menit_terlambat, 1, :now, :now
        )
        RETURNING id_absensi
    """)

    with engine.begin() as conn:
        return conn.execute(sql, {
            "id_pegawai": id_pegawai,
            "tanggal": tanggal,
            "id_jam_kerja": id_jam_kerja,
            "jam_masuk": jam_masuk,
            "jam_keluar": jam_keluar,
            "id_lokasi_masuk": id_lokasi_masuk,
            "id_lokasi_keluar": id_lokasi_keluar,
            "menit_terlambat": menit_terlambat,
            "now": get_wita()
        }).scalar()




def get_pegawai_rekap(id_departemen=None, id_status_pegawai=None):
    sql = """
        SELECT
            p.id_pegawai, p.nip, p.nama_lengkap, nama_panggilan, d.id_departemen, d.nama_departemen, 
            s.id_status_pegawai, s.nama_status
        FROM pegawai p
        LEFT JOIN ref_departemen d
            ON d.id_departemen = p.id_departemen
        LEFT JOIN ref_status_pegawai s
            ON s.id_status_pegawai = p.id_status_pegawai
        WHERE p.status = 1
    """

    params = {}

    if id_departemen:
        sql += " AND p.id_departemen = :id_departemen"
        params["id_departemen"] = id_departemen

    if id_status_pegawai:
        sql += " AND p.id_status_pegawai = :id_status_pegawai"
        params["id_status_pegawai"] = id_status_pegawai

    sql += " ORDER BY p.nama_panggilan ASC"

    with engine.connect() as conn:
        return conn.execute(text(sql), params).mappings().all()



def get_absensi_map(start_date, end_date):
    sql = text("""
        SELECT
            id_pegawai,
            tanggal,
            menit_terlambat
        FROM absensi
        WHERE status = 1
          AND tanggal BETWEEN :start AND :end
    """)

    with engine.connect() as conn:
        rows = conn.execute(sql, {
            "start": start_date,
            "end": end_date
        }).mappings().all()

    result = {}
    for r in rows:
        result.setdefault(r["id_pegawai"], {})[r["tanggal"]] = {
            "menit_terlambat": r["menit_terlambat"]
        }

    return result



def get_izin_map(start_date, end_date):
    sql = text("""
        SELECT id_pegawai, tgl_mulai, tgl_selesai
        FROM izin
        WHERE status = 1
          AND status_approval = 'approved'
          AND tgl_selesai >= :start
          AND tgl_mulai <= :end
    """)

    data = {}
    with engine.connect() as conn:
        for r in conn.execute(sql, {"start": start_date, "end": end_date}):
            current = r.tgl_mulai
            while current <= r.tgl_selesai:
                data.setdefault(r.id_pegawai, set()).add(current)
                current += timedelta(days=1)

    return data


def get_hari_libur_map(start_date, end_date):
    sql = text("""
        SELECT tanggal
        FROM ref_hari_libur
        WHERE status = 1
          AND tanggal BETWEEN :start AND :end
    """)

    with engine.connect() as conn:
        return {r.tanggal for r in conn.execute(sql, {"start": start_date, "end": end_date})}
