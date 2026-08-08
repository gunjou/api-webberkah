import threading
import uuid

from sqlalchemy import text
from datetime import date, timedelta
from calendar import monthrange
from decimal import Decimal

from api.shared.helper import get_wita
from api.utils.config import engine


JOB_STATUS = {}
ACTIVE_JOB = None

SPECIAL_PEGAWAI = {2, 4, 9, 13, 29}

def is_pegawai_special(id_pegawai):
    return id_pegawai in SPECIAL_PEGAWAI

# =========================
# HELPER
# =========================
def count_hari_kerja(start_date, end_date):
    hari = 0
    d = start_date
    while d <= end_date:
        if d.weekday() <= 5:  # Senin–Sabtu
            hari += 1
        d += timedelta(days=1)
    return hari

def count_hari_hadir(status_harian):
    return sum(
        1 for s in status_harian.values()
        if s["status"] in ("HADIR", "CUTI")
    )

def build_status_harian(start_date, end_date, absensi, izin, hari_libur=None):
    """
    hari_libur: set(date) atau list(date)
    """
    if hari_libur is None:
        hari_libur = set()
    else:
        hari_libur = set(hari_libur)

    status = {}

    d = start_date
    while d <= end_date:
        # default
        if d in hari_libur:
            status[d] = {
                "status": "LIBUR",
                "menit_terlambat": 0
            }
        else:
            status[d] = {
                "status": "ALPHA",
                "menit_terlambat": 0
            }
        d += timedelta(days=1)

    # HADIR override
    for a in absensi:
        status[a["tanggal"]] = {
            "status": "HADIR",
            "menit_terlambat": a["menit_terlambat"] or 0
        }

    # IZIN / SAKIT / CUTI override
    for i in izin:
        if i["nama_izin"] in ("Cuti Tahunan", "Cuti Khusus", "Izin Dinas"):
            status[i["tanggal"]] = {"status": "CUTI", "menit_terlambat": 0}
        elif i["nama_izin"] == "Sakit":
            status[i["tanggal"]] = {"status": "SAKIT", "menit_terlambat": 0}
        else:
            status[i["tanggal"]] = {"status": "IZIN", "menit_terlambat": 0}

    return status

def normalize_komponen(komponen):
    hasil = {}
    for k in komponen:
        hasil[k["kode"]] = {
            "nama": k["nama"],
            "bulanan": Decimal(k["nilai"])
        }
    return hasil

def get_persen_telat(menit):
    if menit <= 5:
        return Decimal("0")
    elif menit <= 15:
        return Decimal("0.25")
    elif menit <= 30:
        return Decimal("0.50")
    elif menit <= 45:
        return Decimal("0.75")
    elif menit <= 60:
        return Decimal("0.90")
    else:
        return Decimal("1.00")

def hitung_hari_kerja_efektif(start_date, end_date, hari_libur):
    total = 0
    cur = start_date

    while cur <= end_date:
        if cur.weekday() != 6 and cur not in hari_libur:  # bukan Minggu & bukan libur
            total += 1
        cur += timedelta(days=1)

    return total



# =========================
# MASTER DATA
# =========================
def get_hari_libur_map(start_date, end_date):
    sql = text("""
        SELECT tanggal
        FROM ref_hari_libur
        WHERE status = 1
          AND tanggal BETWEEN :start AND :end
    """)

    with engine.connect() as conn:
        return {r.tanggal for r in conn.execute(sql, {
            "start": start_date,
            "end": end_date
        })}

def get_pegawai_detail(id_pegawai):
    sql = text("""
        SELECT
            p.id_pegawai,
            p.nama_lengkap,
            sp.nama_status
        FROM pegawai p
        JOIN ref_status_pegawai sp ON sp.id_status_pegawai = p.id_status_pegawai
        WHERE p.id_pegawai = :id
          AND p.status = 1
    """)
    with engine.connect() as conn:
        return conn.execute(sql, {"id": id_pegawai}).mappings().first()
    
def get_gaji_dan_komponen(id_pegawai):
    sql = text("""
        SELECT
            'GAPOK' AS kode,
            'Gaji Pokok' AS nama,
            pg.gaji_pokok AS nilai
        FROM pegawai_gaji pg
        WHERE pg.id_pegawai = :id
          AND pg.status = 1

        UNION ALL

        SELECT
            rk.kode,
            rk.nama_komponen,
            pgk.nilai
        FROM pegawai_gaji_komponen pgk
        JOIN ref_komponen_gaji rk ON rk.id_komponen = pgk.id_komponen
        WHERE pgk.id_pegawai = :id
          AND pgk.status = 1
    """)
    with engine.connect() as conn:
        return conn.execute(sql, {"id": id_pegawai}).mappings().all()

def get_absensi(id_pegawai, start_date, end_date):
    sql = text("""
        SELECT
            a.tanggal,
            a.menit_terlambat
        FROM absensi a
        INNER JOIN pegawai p ON p.id_pegawai = a.id_pegawai
        WHERE a.id_pegawai = :id
          AND a.tanggal BETWEEN :start AND :end
          AND a.status = 1
          AND p.status = 1
    """)
    with engine.connect() as conn:
        return conn.execute(sql, {
            "id": id_pegawai,
            "start": start_date,
            "end": end_date
        }).mappings().all()

def get_izin(id_pegawai, start_date, end_date):
    sql = text("""
        SELECT
            r.nama_izin,
            gs::date AS tanggal
        FROM izin i
        JOIN ref_jenis_izin r ON r.id_jenis_izin = i.id_jenis_izin
        JOIN generate_series(i.tgl_mulai, i.tgl_selesai, interval '1 day') gs
            ON TRUE
        WHERE i.id_pegawai = :id
          AND i.status = 1
          AND i.status_approval = 'approved'
          AND gs BETWEEN :start AND :end
    """)
    with engine.connect() as conn:
        return conn.execute(sql, {
            "id": id_pegawai,
            "start": start_date,
            "end": end_date
        }).mappings().all()


# =========================
# SIMULATE PAYROLL (FINAL)
# =========================
def simulate_payroll_harian(
    pegawai,
    komp,
    status_harian
):
    pendapatan = []
    potongan = []

    total_pendapatan = Decimal("0")
    total_potongan = Decimal("0")

    # ambil nilai harian
    gapok = komp.get("GAPOK", {}).get("bulanan", Decimal("0"))
    trp = komp.get("T_TRP", {}).get("bulanan", Decimal("0"))
    mkn = komp.get("T_MKN", {}).get("bulanan", Decimal("0"))

    for tanggal, s in status_harian.items():
        if s["status"] not in ("HADIR", "CUTI"):
            continue

        # PENDAPATAN HARIAN
        total_pendapatan += gapok + trp + mkn

        # TELAT → POTONG TRANSPORT
        if s["status"] == "HADIR" and s["menit_terlambat"] > 0:
            persen = get_persen_telat(s["menit_terlambat"])
            potong = trp * persen

            if potong > 0:
                potongan.append({
                    "tanggal": str(tanggal),
                    "kode": "TELAT_TRP",
                    "nilai": float(round(potong, 2))
                })
                total_potongan += potong

    # ringkas pendapatan (harian × jumlah hari)
    hari_hadir = count_hari_hadir(status_harian)

    pendapatan.append({
        "kode": "GAPOK",
        "nama": "Gaji Pokok",
        "nilai": float(gapok * hari_hadir)
    })
    pendapatan.append({
        "kode": "T_TRP",
        "nama": "Tunjangan Transport",
        "nilai": float(trp * hari_hadir)
    })
    pendapatan.append({
        "kode": "T_MKN",
        "nama": "Tunjangan Makan",
        "nilai": float(mkn * hari_hadir)
    })

    return pendapatan, potongan, total_pendapatan, total_potongan, hari_hadir


def simulate_payroll(id_pegawai, bulan, tahun):
    start_date = date(tahun, bulan, 1)
    if bulan == 12:
        end_date = date(tahun + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = date(tahun, bulan + 1, 1) - timedelta(days=1)

    # =========================
    # AMBIL DATA DASAR
    # =========================
    pegawai = get_pegawai_detail(id_pegawai)
    if not pegawai:
        return {
            "pegawai": {
                "id_pegawai": id_pegawai,
                "nama_lengkap": None,
                "nama_status": None
            },
            "periode": f"{bulan:02d}-{tahun}",
            "pendapatan": [],
            "potongan": [],
            "ringkasan": {
                "total_pendapatan": 0,
                "total_potongan": 0,
                "total_diterima": 0
            },
            "statistik": {
                "total_hari_kerja": 0,
                "total_menit_terlambat": 0
            }
        }
        
    is_special = is_pegawai_special(id_pegawai)

    status_pegawai = pegawai["nama_status"]
    status_harian_based = {"Pegawai Tidak Tetap", "Harian Lepas"}
    status_bulanan_based = {"Pegawai Tetap", "Pegawai Kontrak", "Magang"}

    komponen_raw = get_gaji_dan_komponen(id_pegawai)
    absensi = get_absensi(id_pegawai, start_date, end_date)
    izin = get_izin(id_pegawai, start_date, end_date)

    hari_libur = get_hari_libur_map(start_date, end_date)

    status_harian = build_status_harian(
        start_date,
        end_date,
        absensi,
        izin,
        hari_libur=hari_libur
    )

    hari_kerja_efektif = hitung_hari_kerja_efektif(
        start_date,
        end_date,
        hari_libur
    )

    komp = normalize_komponen(komponen_raw)

    # =========================
    # INISIALISASI
    # =========================
    pendapatan = []
    potongan = []

    total_pendapatan = Decimal("0")
    total_potongan = Decimal("0")

    # =========================
    # PENDAPATAN BULANAN (FULL)
    # =========================
    for kode, k in komp.items():
        pendapatan.append({
            "kode": kode,
            "nama": k["nama"],
            "nilai": float(k["bulanan"])
        })
        total_pendapatan += k["bulanan"]

    # =========================
    # HITUNG NILAI HARIAN
    # =========================
    nilai_harian = {}

    if status_pegawai in status_bulanan_based:
        # bulanan → bagi hari kerja efektif
        for kode in ("T_TRP", "T_MKN"):
            if kode in komp and hari_kerja_efektif > 0:
                nilai_harian[kode] = komp[kode]["bulanan"] / Decimal(hari_kerja_efektif)

    elif status_pegawai in status_harian_based:
        # sudah harian → tidak dibagi
        for kode in ("T_TRP", "T_MKN"):
            if kode in komp:
                nilai_harian[kode] = komp[kode]["bulanan"]

    # =========================
    # LOOP POTONGAN HARIAN
    # =========================
    if not is_special:
        for tanggal, s in status_harian.items():

            # skip minggu & libur nasional
            if tanggal.weekday() == 6 or tanggal in hari_libur:
                continue

            status = s["status"]

            # -------------------------
            # TELAT → POTONG TRANSPORT
            # -------------------------
            if (
                status == "HADIR"
                and s["menit_terlambat"] > 0
                and "T_TRP" in nilai_harian
            ):
                persen = get_persen_telat(s["menit_terlambat"])
                potong = nilai_harian["T_TRP"] * persen

                if potong > 0:
                    potongan.append({
                        "tanggal": tanggal.isoformat(),
                        "kode": "TELAT_TRP",
                        "nilai": float(potong.quantize(Decimal("0.01")))
                    })
                    total_potongan += potong

            # -------------------------
            # IZIN & SAKIT → POTONG TRP & MKN
            # -------------------------
            elif status in ("IZIN", "SAKIT"):
                for kode in ("T_TRP", "T_MKN"):
                    if kode in nilai_harian:
                        potong = nilai_harian[kode]
                        potongan.append({
                            "tanggal": tanggal.isoformat(),
                            "kode": kode,
                            "nilai": float(potong.quantize(Decimal("0.01")))
                        })
                        total_potongan += potong

            # -------------------------
            # ALPHA → POTONG TRP & MKN
            # (PEGAWAI TETAP & MAGANG)
            # -------------------------
            elif status == "ALPHA" and status_pegawai in status_bulanan_based:
                for kode in ("T_TRP", "T_MKN"):
                    if kode in nilai_harian:
                        potong = nilai_harian[kode]
                        potongan.append({
                            "tanggal": tanggal.isoformat(),
                            "kode": kode,
                            "nilai": float(potong.quantize(Decimal("0.01"))),
                            "keterangan": "Alpha"
                        })
                        total_potongan += potong

    # =========================
    # PEGAWAI TIDAK TETAP
    # =========================
    if status_pegawai in status_harian_based:
        pendapatan, potongan, total_pendapatan, total_potongan, hari_kerja_efektif = \
            simulate_payroll_harian(
                pegawai,
                komp,
                status_harian
            )

    # =========================
    # STATISTIK
    # =========================
    if is_special:
        # Pegawai khusus:
        # - dianggap selalu hadir
        # - tidak dihitung keterlambatan
        total_hari_kerja = hari_kerja_efektif
        total_menit_terlambat = 0
    else:
        total_hari_kerja = hitung_hari_kerja_pegawai(status_harian)
        total_menit_terlambat = hitung_total_menit_terlambat(status_harian)

    # =========================
    # RETURN
    # =========================
    return {
        "pegawai": pegawai,
        "periode": f"{bulan:02d}-{tahun}",
        "pendapatan": pendapatan,
        "potongan": potongan,
        "ringkasan": {
            "total_pendapatan": float(total_pendapatan.quantize(Decimal("0.01"))),
            "total_potongan": float(total_potongan.quantize(Decimal("0.01"))),
            "total_diterima": float(
                (total_pendapatan - total_potongan).quantize(Decimal("0.01"))
            )
        },
        "statistik": {
            "total_hari_kerja": total_hari_kerja,
            "total_menit_terlambat": total_menit_terlambat
        }
    }
    


def get_all_pegawai_aktif():
    sql = text("""
        SELECT id_pegawai
        FROM pegawai
        WHERE status = 1
    """)
    with engine.connect() as conn:
        return [r["id_pegawai"] for r in conn.execute(sql).mappings().all()]


def get_or_create_payroll_periode(bulan, tahun):
    sql_check = text("""
        SELECT id_periode
        FROM payroll_periode
        WHERE bulan = :bulan AND tahun = :tahun AND status = 1
        LIMIT 1
    """)
    with engine.connect() as conn:
        row = conn.execute(sql_check, {
            "bulan": bulan,
            "tahun": tahun
        }).mappings().first()

    if row:
        return row["id_periode"]

    sql_insert = text("""
        INSERT INTO payroll_periode (bulan, tahun, tanggal_proses)
        VALUES (:bulan, :tahun, CURRENT_DATE)
        RETURNING id_periode
    """)
    with engine.begin() as conn:
        row = conn.execute(sql_insert, {
            "bulan": bulan,
            "tahun": tahun
        }).mappings().first()

    return row["id_periode"]

def hitung_hari_kerja_pegawai(status_harian):
    return sum(
        1 for s in status_harian.values()
        if s["status"] in ("HADIR", "CUTI")
    )

def hitung_total_menit_terlambat(status_harian):
    return sum(
        s["menit_terlambat"]
        for s in status_harian.values()
        if s["status"] == "HADIR"
    )
    
def get_existing_payroll(id_pegawai, id_periode):
    sql = text("""
        SELECT id_payroll
        FROM payroll
        WHERE id_pegawai = :id_pegawai
          AND id_periode = :id_periode
          AND status = 1
        LIMIT 1
    """)
    with engine.connect() as conn:
        row = conn.execute(sql, {
            "id_pegawai": id_pegawai,
            "id_periode": id_periode
        }).mappings().first()

    return row["id_payroll"] if row else None

def update_payroll(id_payroll, ringkasan, statistik):
    sql = text("""
        UPDATE payroll
        SET
            total_pendapatan = :pendapatan,
            total_potongan = :potongan,
            total_diterima = :diterima,
            total_hari_kerja = :hari_kerja,
            total_menit_terlambat = :menit_telat,
            updated_at = :now
        WHERE id_payroll = :id_payroll
    """)
    print("DEBUG: update_payroll", id_payroll, ringkasan, statistik)
    return sql, {
        "id_payroll": id_payroll,
        "pendapatan": ringkasan["total_pendapatan"],
        "potongan": ringkasan["total_potongan"],
        "diterima": ringkasan["total_diterima"],
        "hari_kerja": statistik["total_hari_kerja"],
        "menit_telat": statistik["total_menit_terlambat"],
        "now": get_wita()
    }

def delete_payroll_detail(id_payroll):
    return text("""
        DELETE FROM payroll_detail
        WHERE id_payroll = :id_payroll
    """), {"id_payroll": id_payroll}


def delete_payroll_potongan_detail(id_payroll):
    return text("""
        DELETE FROM payroll_potongan_detail
        WHERE id_payroll = :id_payroll
    """), {"id_payroll": id_payroll}


def insert_payroll(id_pegawai, id_periode, ringkasan, statistik):
    sql = text("""
        INSERT INTO payroll (
            id_pegawai, id_periode,
            total_pendapatan, total_potongan, total_diterima,
            total_hari_kerja, total_menit_terlambat
        )
        VALUES (
            :id_pegawai, :id_periode,
            :pendapatan, :potongan, :diterima,
            :hari_kerja, :menit_telat
        )
        RETURNING id_payroll
    """)
    print("DEBUG: insert_payroll", id_pegawai, id_periode, ringkasan, statistik)

    params = {
        "id_pegawai": id_pegawai,
        "id_periode": id_periode,
        "pendapatan": ringkasan["total_pendapatan"],
        "potongan": ringkasan["total_potongan"],
        "diterima": ringkasan["total_diterima"],
        "hari_kerja": statistik["total_hari_kerja"],
        "menit_telat": statistik["total_menit_terlambat"]
    }

    return sql, params


def insert_payroll_detail(id_payroll, pendapatan):
    sql = text("""
        INSERT INTO payroll_detail (
            id_payroll, kode_komponen, nama_komponen, nilai
        )
        VALUES (
            :id_payroll, :kode, :nama, :nilai
        )
    """)
    print("DEBUG: insert_payroll_detail", id_payroll, pendapatan)
    return [
        (sql, {
            "id_payroll": id_payroll,
            "kode": p["kode"],
            "nama": p["nama"],
            "nilai": p["nilai"]
        })
        for p in pendapatan
    ]

def insert_payroll_potongan_detail(id_payroll, potongan):
    sql = text("""
        INSERT INTO payroll_potongan_detail (
            id_payroll, tanggal, kode_potongan,
            nama_potongan, nilai, keterangan
        )
        VALUES (
            :id_payroll, :tanggal, :kode,
            :nama, :nilai, :ket
        )
    """)
    return [
        (sql, {
            "id_payroll": id_payroll,
            "tanggal": p["tanggal"],
            "kode": p["kode"],
            "nama": p["kode"],
            "nilai": p["nilai"],
            "ket": None
        })
        for p in potongan
    ]

# def generate_payroll(bulan, tahun):
#     id_periode = get_or_create_payroll_periode(bulan, tahun)
#     pegawai_list = get_all_pegawai_aktif()

#     total_pegawai = 0
#     updated = 0
#     inserted = 0

#     # =========================
#     # 🔥 STEP 1: SIMULATE (NO TRANSACTION)
#     # =========================
#     hasil_simulasi = {}

#     for id_pegawai in pegawai_list:
#         print(f"Simulating payroll for id_pegawai={id_pegawai}...")
#         hasil_simulasi[id_pegawai] = simulate_payroll(id_pegawai, bulan, tahun)

#     # =========================
#     # 🔥 STEP 2: WRITE (TRANSACTION)
#     # =========================
#     with engine.begin() as conn:

#         for id_pegawai in pegawai_list:
#             result = hasil_simulasi[id_pegawai]

#             existing_id = get_existing_payroll(id_pegawai, id_periode)

#             # =====================
#             # UPSERT HEADER
#             # =====================
#             if existing_id:
#                 sql, params = update_payroll(
#                     existing_id,
#                     result["ringkasan"],
#                     result["statistik"]
#                 )
#                 conn.execute(sql, params)

#                 sql, params = delete_payroll_detail(existing_id)
#                 conn.execute(sql, params)

#                 sql, params = delete_payroll_potongan_detail(existing_id)
#                 conn.execute(sql, params)

#                 id_payroll = existing_id
#                 updated += 1

#             else:
#                 sql, params = insert_payroll(
#                     id_pegawai,
#                     id_periode,
#                     result["ringkasan"],
#                     result["statistik"]
#                 )
#                 row = conn.execute(sql, params).mappings().first()
#                 id_payroll = row["id_payroll"]
#                 inserted += 1

#             # =====================
#             # INSERT DETAIL
#             # =====================
#             detail_list = insert_payroll_detail(
#                 id_payroll, result["pendapatan"]
#             )

#             if detail_list:
#                 for sql, p in detail_list:
#                     conn.execute(sql, p)

#             potongan_list = insert_payroll_potongan_detail(
#                 id_payroll, result["potongan"]
#             )

#             if potongan_list:
#                 for sql, p in potongan_list:
#                     conn.execute(sql, p)

#             total_pegawai += 1

#     return {
#         "periode": f"{bulan:02d}-{tahun}",
#         "total_pegawai": total_pegawai,
#         "inserted": inserted,
#         "updated": updated
#     }


def generate_payroll_with_job(bulan, tahun):
    job_id = str(uuid.uuid4())

    JOB_STATUS[job_id] = {
        "status": "starting",
        "progress": 0,
        "total": 0,
        "current": 0,
        "step": "init",
        # "started_at": get_wita()
    }

    # 🔥 JALANKAN DI BACKGROUND
    thread = threading.Thread(
        target=run_generate_payroll_job,
        args=(job_id, bulan, tahun)
    )
    thread.start()

    # 🔥 LANGSUNG RETURN (INI YANG KAMU MAU)
    return job_id


def run_generate_payroll_job(job_id, bulan, tahun):
    global ACTIVE_JOB
    
    try:
        id_periode = get_or_create_payroll_periode(bulan, tahun)
        pegawai_list = get_all_pegawai_aktif()

        total = len(pegawai_list)

        JOB_STATUS[job_id].update({
            "status": "running",
            "total": total,
            "current": 0,
            "progress": 0,
            "step": "simulate"
        })
        
        total_pegawai = 0
        updated = 0
        inserted = 0

        hasil_simulasi = {}

        # =========================
        # STEP 1: SIMULATE
        # =========================
        for i, id_pegawai in enumerate(pegawai_list):
            hasil_simulasi[id_pegawai] = simulate_payroll(id_pegawai, bulan, tahun)

            JOB_STATUS[job_id]["current"] = i + 1
            JOB_STATUS[job_id]["progress"] = int(((i + 1) / total) * 50)

        # =========================
        # STEP 2: WRITE
        # =========================
        JOB_STATUS[job_id]["step"] = "writing"

        with engine.begin() as conn:
            for i, id_pegawai in enumerate(pegawai_list):
                result = hasil_simulasi[id_pegawai]

                existing_id = get_existing_payroll(id_pegawai, id_periode)

                if existing_id:
                    sql, params = update_payroll(
                        existing_id,
                        result["ringkasan"],
                        result["statistik"]
                    )
                    conn.execute(sql, params)

                    sql, params = delete_payroll_detail(existing_id)
                    conn.execute(sql, params)

                    sql, params = delete_payroll_potongan_detail(existing_id)
                    conn.execute(sql, params)

                    id_payroll = existing_id
                    updated += 1
                else:
                    sql, params = insert_payroll(
                        id_pegawai,
                        id_periode,
                        result["ringkasan"],
                        result["statistik"]
                    )
                    row = conn.execute(sql, params).mappings().first()
                    id_payroll = row["id_payroll"]
                    inserted += 1

                for sql, p in insert_payroll_detail(id_payroll, result["pendapatan"]):
                    conn.execute(sql, p)

                for sql, p in insert_payroll_potongan_detail(id_payroll, result["potongan"]):
                    conn.execute(sql, p)

                total_pegawai += 1

                JOB_STATUS[job_id]["current"] = i + 1
                JOB_STATUS[job_id]["progress"] = 50 + int(((i + 1) / total) * 50)

        JOB_STATUS[job_id].update({
            "status": "done",
            "progress": 100,
            "result": {
                "periode": f"{bulan:02d}-{tahun}",
                "total_pegawai": total_pegawai,
                "inserted": inserted,
                "updated": updated
            }
        })
        
        ACTIVE_JOB = None

    except Exception as e:
        JOB_STATUS[job_id].update({
            "status": "error",
            "error": str(e)
        })
        ACTIVE_JOB = None
        

# def run_generate_payroll_job(job_id, bulan, tahun):
#     # inisialisasi status awal
#     JOB_STATUS[job_id] = {
#         "status": "starting",
#         "progress": 0,
#         "total": 0,
#         "current": 0,
#         "step": "init"
#     }
    
#     print(JOB_STATUS)

#     try:
#         id_periode = get_or_create_payroll_periode(bulan, tahun)
#         pegawai_list = get_all_pegawai_aktif()

#         total = len(pegawai_list)

#         JOB_STATUS[job_id].update({
#             "status": "running",
#             "total": total,
#             "current": 0,
#             "progress": 0,
#             "step": "simulate"
#         })

#         total_pegawai = 0
#         updated = 0
#         inserted = 0

#         # =========================
#         # 🔥 STEP 1: SIMULATE
#         # =========================
#         hasil_simulasi = {}

#         for i, id_pegawai in enumerate(pegawai_list):
#             print(f"[SIMULATE] id_pegawai={id_pegawai}")

#             hasil_simulasi[id_pegawai] = simulate_payroll(id_pegawai, bulan, tahun)

#             # update progress (0–50%)
#             JOB_STATUS[job_id]["current"] = i + 1
#             JOB_STATUS[job_id]["progress"] = int(((i + 1) / total) * 50)

#         # =========================
#         # 🔥 STEP 2: WRITE
#         # =========================
#         JOB_STATUS[job_id]["step"] = "writing"

#         with engine.begin() as conn:

#             for i, id_pegawai in enumerate(pegawai_list):
#                 result = hasil_simulasi[id_pegawai]

#                 existing_id = get_existing_payroll(id_pegawai, id_periode)

#                 # =====================
#                 # UPSERT HEADER
#                 # =====================
#                 if existing_id:
#                     sql, params = update_payroll(
#                         existing_id,
#                         result["ringkasan"],
#                         result["statistik"]
#                     )
#                     conn.execute(sql, params)

#                     sql, params = delete_payroll_detail(existing_id)
#                     conn.execute(sql, params)

#                     sql, params = delete_payroll_potongan_detail(existing_id)
#                     conn.execute(sql, params)

#                     id_payroll = existing_id
#                     updated += 1

#                 else:
#                     sql, params = insert_payroll(
#                         id_pegawai,
#                         id_periode,
#                         result["ringkasan"],
#                         result["statistik"]
#                     )
#                     row = conn.execute(sql, params).mappings().first()
#                     id_payroll = row["id_payroll"]
#                     inserted += 1

#                 # =====================
#                 # INSERT DETAIL
#                 # =====================
#                 detail_list = insert_payroll_detail(
#                     id_payroll, result["pendapatan"]
#                 )

#                 if detail_list:
#                     for sql, p in detail_list:
#                         conn.execute(sql, p)

#                 potongan_list = insert_payroll_potongan_detail(
#                     id_payroll, result["potongan"]
#                 )

#                 if potongan_list:
#                     for sql, p in potongan_list:
#                         conn.execute(sql, p)

#                 total_pegawai += 1

#                 # update progress (50–100%)
#                 JOB_STATUS[job_id]["current"] = i + 1
#                 JOB_STATUS[job_id]["progress"] = 50 + int(((i + 1) / total) * 50)

#         # =========================
#         # DONE
#         # =========================
#         JOB_STATUS[job_id].update({
#             "status": "done",
#             "progress": 100,
#             "result": {
#                 "periode": f"{bulan:02d}-{tahun}",
#                 "total_pegawai": total_pegawai,
#                 "inserted": inserted,
#                 "updated": updated
#             }
#         })

#     except Exception as e:
#         JOB_STATUS[job_id].update({
#             "status": "error",
#             "error": str(e)
#         })



def get_payroll_periode(bulan, tahun):
    sql = text("""
        SELECT id_periode
        FROM payroll_periode
        WHERE bulan = :bulan
          AND tahun = :tahun
          AND status = 1
        LIMIT 1
    """)
    with engine.connect() as conn:
        row = conn.execute(sql, {
            "bulan": bulan,
            "tahun": tahun
        }).mappings().first()

    return row["id_periode"] if row else None

def get_payroll_list(id_periode):
    sql = text("""
        SELECT
            pr.id_payroll,
            p.id_pegawai,
            p.nama_lengkap,
            sp.nama_status,
            pr.total_pendapatan,
            pr.total_potongan,
            pr.total_diterima,
            pr.total_hari_kerja,
            pr.total_menit_terlambat,
            pr.updated_at
        FROM payroll pr
        JOIN pegawai p ON p.id_pegawai = pr.id_pegawai
        JOIN ref_status_pegawai sp ON sp.id_status_pegawai = p.id_status_pegawai
        WHERE pr.id_periode = :id_periode
        AND pr.status = 1
        ORDER BY p.nama_lengkap
    """)
    with engine.connect() as conn:
        return conn.execute(sql, {
            "id_periode": id_periode
        }).mappings().all()

def get_payroll_summary(id_periode):
    sql = text("""
        SELECT
            COUNT(*) AS jumlah_pegawai,
            COALESCE(SUM(total_pendapatan), 0) AS total_pendapatan,
            COALESCE(SUM(total_potongan), 0) AS total_potongan,
            COALESCE(SUM(total_diterima), 0) AS total_diterima
        FROM payroll
        WHERE id_periode = :id_periode
          AND status = 1
    """)
    with engine.connect() as conn:
        return conn.execute(sql, {
            "id_periode": id_periode
        }).mappings().first()

def get_payroll_by_periode(bulan, tahun):
    id_periode = get_payroll_periode(bulan, tahun)

    if not id_periode:
        return {
            "periode": f"{bulan:02d}-{tahun}",
            "summary": {
                "jumlah_pegawai": 0,
                "total_pendapatan": 0,
                "total_potongan": 0,
                "total_diterima": 0
            },
            "data": []
        }

    data_raw = get_payroll_list(id_periode)
    summary = get_payroll_summary(id_periode)
    rekap_map = get_rekap_status_payroll(bulan, tahun)

    data = []

    for row in data_raw:
        row_dict = dict(row)

        r = rekap_map.get(row_dict["id_pegawai"], {})

        row_dict["total_hadir"] = r.get("total_hadir", 0)
        row_dict["total_izin"] = r.get("total_izin", 0)
        row_dict["total_sakit"] = r.get("total_sakit", 0)
        row_dict["total_cuti"] = r.get("total_cuti", 0)

        alpha = r.get("total_alpha", 0) or 0
        row_dict["total_alpha"] = max(0, alpha)

        data.append(row_dict)

    return {
        "periode": f"{bulan:02d}-{tahun}",
        "summary": summary,
        "data": data
    }

def get_rekap_status_payroll(bulan, tahun):
    start_date = date(tahun, bulan, 1)
    last_day = monthrange(tahun, bulan)[1]
    end_date = date(tahun, bulan, last_day)

    sql = text("""
        WITH hari_kerja AS (
            SELECT
                p.id_pegawai,
                COUNT(d::date) AS total_hari_kerja
            FROM pegawai p,
            generate_series(:start, :end, interval '1 day') d
            WHERE p.status = 1
              AND EXTRACT(DOW FROM d) != 0
              AND d::date NOT IN (
                  SELECT tanggal
                  FROM ref_hari_libur
                  WHERE status = 1
                    AND tanggal BETWEEN :start AND :end
              )
            GROUP BY p.id_pegawai
        ),
        hadir AS (
            SELECT id_pegawai, COUNT(*) AS total_hadir
            FROM absensi
            WHERE status = 1
              AND tanggal BETWEEN :start AND :end
            GROUP BY id_pegawai
        ),
        izin AS (
            SELECT
                i.id_pegawai,
                SUM(CASE WHEN i.id_jenis_izin IN (1,2,6) THEN 1 ELSE 0 END) AS total_izin,
                SUM(CASE WHEN i.id_jenis_izin = 3 THEN 1 ELSE 0 END) AS total_sakit,
                SUM(CASE WHEN i.id_jenis_izin IN (4,5) THEN 1 ELSE 0 END) AS total_cuti
            FROM izin i
            JOIN generate_series(i.tgl_mulai, i.tgl_selesai, interval '1 day') d
                ON TRUE
            WHERE i.status = 1
              AND i.status_approval = 'approved'
              AND d::date BETWEEN :start AND :end
            GROUP BY i.id_pegawai
        )
        SELECT
            hk.id_pegawai,
            hk.total_hari_kerja,
            COALESCE(h.total_hadir, 0) AS total_hadir,
            COALESCE(iz.total_izin, 0) AS total_izin,
            COALESCE(iz.total_sakit, 0) AS total_sakit,
            COALESCE(iz.total_cuti, 0) AS total_cuti,
            (
                hk.total_hari_kerja
                - COALESCE(h.total_hadir, 0)
                - COALESCE(iz.total_izin, 0)
                - COALESCE(iz.total_sakit, 0)
                - COALESCE(iz.total_cuti, 0)
            ) AS total_alpha
        FROM hari_kerja hk
        LEFT JOIN hadir h ON h.id_pegawai = hk.id_pegawai
        LEFT JOIN izin iz ON iz.id_pegawai = hk.id_pegawai
    """)

    with engine.connect() as conn:
        rows = conn.execute(sql, {
            "start": start_date,
            "end": end_date
        }).mappings().all()

    return {r["id_pegawai"]: r for r in rows}




def get_all_pegawai_basic():
    sql = text("""
        SELECT id_pegawai, nama_lengkap
        FROM pegawai
        WHERE status = 1
        ORDER BY nama_lengkap ASC
    """)
    with engine.connect() as conn:
        return conn.execute(sql).mappings().all()

def get_all_gapok():
    sql = text("""
        SELECT id_pegawai, gaji_pokok
        FROM pegawai_gaji
        WHERE status = 1
    """)
    with engine.connect() as conn:
        rows = conn.execute(sql).mappings().all()

    return {r["id_pegawai"]: r["gaji_pokok"] for r in rows}

def get_all_komponen_gaji():
    sql = text("""
        SELECT
            pgk.id_pegawai,
            rk.kode,
            rk.nama_komponen,
            pgk.nilai
        FROM pegawai_gaji_komponen pgk
        JOIN ref_komponen_gaji rk
            ON rk.id_komponen = pgk.id_komponen
        WHERE pgk.status = 1
          AND rk.status = 1
        ORDER BY rk.kode ASC
    """)
    with engine.connect() as conn:
        return conn.execute(sql).mappings().all()

def get_komponen_gaji_semua_pegawai():
    pegawai_list = get_all_pegawai_basic()
    gapok_map = get_all_gapok()
    komponen_rows = get_all_komponen_gaji()

    # group komponen by id_pegawai
    komponen_map = {}
    for k in komponen_rows:
        komponen_map.setdefault(k["id_pegawai"], []).append({
            "kode": k["kode"],
            "nama": k["nama_komponen"],
            "nilai": k["nilai"]
        })

    result = []

    for p in pegawai_list:
        id_pegawai = p["id_pegawai"]

        komponen = []

        # GAPOK
        if id_pegawai in gapok_map:
            komponen.append({
                "kode": "GAPOK",
                "nama": "Gaji Pokok",
                "nilai": gapok_map[id_pegawai]
            })

        # Komponen lain
        komponen.extend(komponen_map.get(id_pegawai, []))

        result.append({
            "id_pegawai": id_pegawai,
            "nama_lengkap": p["nama_lengkap"],
            "komponen_gaji": komponen
        })

    return {
        "jumlah_pegawai": len(result),
        "data": result
    }
