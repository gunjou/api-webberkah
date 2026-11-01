from calendar import monthrange
from functools import wraps
import os
import time as time_module
import traceback
from dotenv import load_dotenv
from flask_restx import Namespace, Resource
from flask import request, g
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import date, datetime, time, timedelta
from flask_restx import reqparse
from werkzeug.datastructures import FileStorage
from werkzeug.exceptions import BadRequest, HTTPException

from api.shared.exceptions import AppError
from api.shared.helper import count_hari_dalam_bulan, get_wita
from api.shared.response import success
from api.utils.decorator import measure_execution_time, role_required
from api.query.q_absensi import *
from api.query.q_absensi_log import *
from api.query.q_lembur import insert_pengajuan_lembur
from api.utils.face import verify_face
from api.utils.geo import find_valid_lokasi
from api.utils.time_calc import *

absensi_ns = Namespace("absensi", description="Absensi Pegawai")

load_dotenv()

validate_parser = reqparse.RequestParser()
validate_parser.add_argument("file", type=FileStorage, location="files", required=True, help="Foto wajah pegawai")
validate_parser.add_argument("latitude", type=float, location="form", required=True, help="Latitude lokasi absensi")
validate_parser.add_argument("longitude", type=float, location="form", required=True, help="Longitude lokasi absensi")
validate_parser.add_argument("id_jam_kerja", type=int, required=False, help="ID jam kerja (opsional, default Normal)")

absensi_basic_parser = reqparse.RequestParser()
absensi_basic_parser.add_argument("tanggal", type=str, required=False, location="args", help="format: YYYY-MM-DD")

absensi_bulanan_parser = absensi_ns.parser()
absensi_bulanan_parser.add_argument("bulan", type=int, required=False, help="Bulan (1-12)")
absensi_bulanan_parser.add_argument("tahun", type=int, required=False, help="Tahun (YYYY)")


# ==================================================
# ERROR ABSENSI
# ==================================================
# Setiap error punya `error_code` tetap supaya frontend bisa membedakan
# kasus tanpa mem-parsing teks pesan. Status HTTP:
#   400 input tidak valid, 403 tidak diizinkan, 404 data tidak ada,
#   409 urutan/status absensi tidak sesuai, 422 verifikasi gagal (wajah, lokasi, jam)
class AbsensiError(AppError):
    def __init__(self, message, code, status_code=422, errors=None):
        super().__init__(message=message, code=code, status_code=status_code, errors=errors)


def parse_form_absensi():
    """Parse form absensi; field yang kurang/salah dikembalikan dalam format error standar."""
    try:
        return validate_parser.parse_args()
    except BadRequest as e:
        detail = (getattr(e, "data", None) or {}).get("errors") or {}
        raise AbsensiError(
            "Data absensi tidak lengkap. Pastikan foto wajah, latitude, dan longitude terkirim",
            "INVALID_INPUT",
            400,
            errors={"fields": list(detail.keys())}
        )


def parse_tanggal(tanggal_str):
    try:
        return datetime.strptime(tanggal_str, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        raise AbsensiError(
            f"Format tanggal '{tanggal_str}' tidak valid, gunakan YYYY-MM-DD",
            "INVALID_DATE",
            400
        )


def parse_bulan_tahun(args, now):
    bulan = args.get("bulan") or now.month
    tahun = args.get("tahun") or now.year
    if not 1 <= bulan <= 12:
        raise AbsensiError("Bulan harus bernilai 1 sampai 12", "INVALID_MONTH", 400)
    if not 2000 <= tahun <= 2100:
        raise AbsensiError("Tahun tidak valid", "INVALID_YEAR", 400)
    return bulan, tahun


def raise_absensi_tidak_aktif(id_pegawai: int, tanggal: date, aksi: str):
    """Bedakan 'belum check-in' dan 'sudah check-out' agar pesan ke pegawai tepat."""
    absensi_hari_ini = get_absensi_hari_ini(id_pegawai, tanggal)
    if absensi_hari_ini and absensi_hari_ini["jam_keluar"] is not None:
        raise AbsensiError(
            f"Anda sudah check-out hari ini pukul "
            f"{absensi_hari_ini['jam_keluar'].strftime('%H:%M')} WITA, tidak dapat {aksi}",
            "ALREADY_CHECKED_OUT",
            409
        )
    raise AbsensiError(
        f"Anda belum check-in hari ini. Silakan check-in terlebih dahulu sebelum {aksi}",
        "NOT_CHECKED_IN",
        409
    )


# ==================================================
# LOG ERROR ABSENSI
# ==================================================
# Setiap aksi absen yang gagal dicatat ke tabel absensi_log.
# Handler dapat mengisi g.absensi_log["id_absensi"] / ["id_jam_kerja"]
# supaya log menunjuk ke absensi terkait.
def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def simpan_log_error(aksi, start, http_status, error_code, message, errors=None, detail_teknis=None):
    # Log tidak boleh menggagalkan response ke pegawai
    try:
        ctx = getattr(g, "absensi_log", {}) or {}
        insert_absensi_log(
            id_pegawai=int(get_jwt_identity()),
            aksi=aksi,
            berhasil=False,
            http_status=http_status,
            error_code=error_code,
            message=message,
            errors=errors,
            latitude=_to_float(request.form.get("latitude")),
            longitude=_to_float(request.form.get("longitude")),
            id_absensi=ctx.get("id_absensi"),
            id_jam_kerja=ctx.get("id_jam_kerja") or _to_int(request.form.get("id_jam_kerja")),
            durasi_ms=int((time_module.perf_counter() - start) * 1000),
            detail_teknis=detail_teknis
        )
    except Exception:
        print(f"[absensi_log] gagal menyimpan log {aksi}:\n{traceback.format_exc()}")


def log_absensi(aksi: str):
    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            g.absensi_log = {}
            start = time_module.perf_counter()
            try:
                return fn(*args, **kwargs)
            except AppError as e:
                simpan_log_error(aksi, start, e.status_code, e.code, e.message, e.errors)
                raise
            except HTTPException as e:
                simpan_log_error(aksi, start, e.code or 500, "HTTP_ERROR", e.description)
                raise
            except Exception:
                simpan_log_error(
                    aksi, start, 500, "INTERNAL_ERROR",
                    "Terjadi kesalahan pada server",
                    detail_teknis=traceback.format_exc()
                )
                raise
        return decorator
    return wrapper


def verify_wajah_absensi(id_pegawai: int, file) -> None:
    if not verify_face(id_pegawai, file):
        raise AbsensiError(
            "Wajah tidak cocok dengan data pegawai. Pastikan wajah terlihat jelas dan coba lagi",
            "FACE_MISMATCH",
            422
        )



# ==================================================
# FUNGSI HELPER UNTUK VALIDASI LOKASI
# ==================================================
def validate_lokasi_absensi(
    id_pegawai: int,
    latitude: float,
    longitude: float
) -> dict:

    # =====================================================
    # 1. Ambil semua lokasi aktif
    # =====================================================

    all_lokasi = get_all_lokasi_absensi()

    # =====================================================
    # 2. Ambil lokasi yang boleh digunakan pegawai
    # =====================================================

    allowed_lokasi_ids = get_allowed_lokasi_ids_pegawai(
        id_pegawai
    )

    # =====================================================
    # 3. Cari lokasi TERDEKAT
    # =====================================================

    lokasi_result = find_valid_lokasi(
        latitude=latitude,
        longitude=longitude,
        lokasi_list=all_lokasi,
        allowed_lokasi_ids=allowed_lokasi_ids
    )

    # =====================================================
    # 4. Tidak ada lokasi fisik yang bisa digunakan
    # =====================================================

    if lokasi_result is None:

        if is_pegawai_wfh(id_pegawai):
            return {
                "id_lokasi": os.getenv("ID_LOKASI_WFH"),
                "nama_lokasi": "WFH",
                "is_wfh": True
            }

        raise AbsensiError(
            "Anda belum memiliki lokasi absensi yang terdaftar. Hubungi admin/HR",
            "LOCATION_NOT_REGISTERED",
            403
        )

    # =====================================================
    # 5. LOKASI VALID
    # =====================================================

    if lokasi_result["valid"]:

        lokasi_result["is_wfh"] = False

        return lokasi_result

    # =====================================================
    # 6. LOKASI TERDEKAT TAPI DI LUAR RADIUS
    # =====================================================

    lokasi_terdekat = lokasi_result["terdekat"]

    nama_lokasi = lokasi_terdekat["nama_lokasi"]
    jarak = lokasi_terdekat["jarak"]
    radius = lokasi_terdekat["radius_meter"]
    jarak_di_luar = lokasi_terdekat["jarak_di_luar_radius"]
    arah = lokasi_terdekat["arah"]

    # =====================================================
    # 7. Jika pegawai WFH, tetap izinkan WFH
    # =====================================================

    if is_pegawai_wfh(id_pegawai):
        return {
            "id_lokasi": os.getenv("ID_LOKASI_WFH"),
            "nama_lokasi": "WFH",
            "is_wfh": True
        }

    # =====================================================
    # 8. ERROR
    # =====================================================
    # Minimal 1 meter agar pesan tidak menyebut "0 meter" saat tepat di tepi radius
    kurang_meter = max(1, round(jarak_di_luar))
    raise AbsensiError(
        f"Anda berada di luar radius absensi {nama_lokasi}. "
        f"Kurang sekitar {kurang_meter} meter ke arah {arah}. "
        f"Jarak Anda ke {nama_lokasi} {jarak:.0f} meter, maksimal {radius} meter",
        "OUTSIDE_RADIUS",
        422,
        errors={
            "lokasi_terdekat": nama_lokasi,
            "jarak_meter": round(jarak),
            "radius_meter": radius,
            "jarak_di_luar_radius_meter": kurang_meter,
            "arah": arah,
            "arah_derajat": lokasi_terdekat["arah_derajat"]
        }
    )
        # f"(radius maksimal {radius} meter). "
        # f"Silakan mendekat sekitar "
        # f"{jarak_di_luar:.2f} meter."

def get_tanggal_absensi(now, jam_mulai_shift):
    """
    Menentukan tanggal absensi berdasarkan jam mulai shift.
    Aturan:
    - Jika waktu sekarang >= jam mulai shift → tanggal hari ini
    - Jika waktu sekarang < jam mulai shift → tanggal kemarin
      (khusus shift lintas hari / malam)
    """

    # Shift normal / sore (tidak lintas hari)
    jam_mulai_dt = datetime.combine(now.date(), jam_mulai_shift)
    batas_mulai = jam_mulai_dt - timedelta(hours=2)

    # Shift normal / sore (tidak lintas hari)
    if now >= batas_mulai:
        return now.date()

    return (now - timedelta(days=1)).date()


# ==================================================
# JADWAL & VALIDASI WAKTU ISTIRAHAT (WITA)
# ==================================================
# Jendela waktu inklusif per menit: (jam_awal, jam_akhir).
# Contoh 12:00 - 12:30 → 12:00:00 s/d 12:30:59 masih diterima.
JADWAL_ISTIRAHAT = {
    "normal": {
        "mulai": (time(12, 0), time(12, 30)),
        "selesai": (time(13, 30), time(14, 0)),
    },
    "jumat": {
        "mulai": (time(11, 30), time(12, 30)),
        "selesai": (time(13, 30), time(14, 0)),
    },
}


def get_jendela_istirahat(tanggal: date, jenis: str) -> tuple:
    """jenis: 'mulai' atau 'selesai'. Jumat = weekday() 4."""
    hari = "jumat" if tanggal.weekday() == 4 else "normal"
    return JADWAL_ISTIRAHAT[hari][jenis]


def validate_jam_istirahat(now: datetime, jenis: str) -> None:
    jam_awal, jam_akhir = get_jendela_istirahat(now.date(), jenis)
    jam_sekarang = now.time().replace(second=0, microsecond=0)

    if not (jam_awal <= jam_sekarang <= jam_akhir):
        label = "Mulai" if jenis == "mulai" else "Selesai"
        posisi = "belum dibuka" if jam_sekarang < jam_awal else "sudah ditutup"
        raise AbsensiError(
            f"{label} istirahat hanya dapat dilakukan pukul "
            f"{jam_awal.strftime('%H:%M')} - {jam_akhir.strftime('%H:%M')} WITA "
            f"(sekarang {jam_sekarang.strftime('%H:%M')}, waktu {posisi})",
            "BREAK_START_OUT_OF_WINDOW" if jenis == "mulai" else "BREAK_END_OUT_OF_WINDOW",
            422,
            errors={
                "jam_awal": jam_awal.strftime("%H:%M"),
                "jam_akhir": jam_akhir.strftime("%H:%M"),
                "jam_sekarang": jam_sekarang.strftime("%H:%M")
            }
        )


# ==================================================
# GET ABSENSI HARIAN UNTUK KEPERLUAN ABSEN
# ==================================================
@absensi_ns.route("/hari-ini")
class AbsensiHariIniResource(Resource):
    
    @jwt_required()
    @measure_execution_time
    def get(self):
        """(pegawai) Ambil status absensi harian --> absen"""
        id_pegawai = int(get_jwt_identity())
        now = get_wita()

        # 1️⃣ Ambil absensi aktif dulu (penting untuk shift malam)
        data = get_active_absensi_untuk_harian(id_pegawai)

        # 2️⃣ Jika tidak ada absensi aktif, fallback ke tanggal
        if not data:
            tanggal_str = request.args.get("tanggal")
            if tanggal_str:
                tanggal = parse_tanggal(tanggal_str)
            else:
                tanggal = now.date()

            data = get_absensi_harian(id_pegawai, tanggal)
            
        is_shift = has_active_shift(id_pegawai)

        # jika belum ada absensi sama sekali
        if not data or not data["id_absensi"]:
            return success(
                data={
                    "pegawai": {
                        "id_pegawai": id_pegawai,
                        "nama_lengkap": data["nama_lengkap"] if data else None,
                        "nama_panggilan": data["nama_panggilan"] if data else None,
                        "is_shift": is_shift if is_shift else None
                    },
                    "tanggal": tanggal.isoformat(),
                    "jam_kerja": None,
                    "presensi": None
                },
                message="Belum ada data absensi pada tanggal ini"
            )

        # ambil data istirahat
        istirahat = get_istirahat_absensi(data["id_absensi"])
        
        jam_selesai_istirahat_terakhir = None
        if istirahat:
            for i in reversed(istirahat):
                if i["jam_selesai"]:
                    jam_selesai_istirahat_terakhir = i["jam_selesai"]
                    break
                
        terlambat_istirahat = hitung_terlambat_istirahat(jam_selesai_istirahat_terakhir)

        return success(
            data={
                "tanggal": data["tanggal"].isoformat(),
                "pegawai": {
                    "id_pegawai": data["id_pegawai"],
                    "nama_lengkap": data["nama_lengkap"],
                    "nama_panggilan": data["nama_panggilan"],
                    "is_shift": is_shift if is_shift else None,
                },
                "jam_kerja": {
                    "id_jam_kerja": data["id_jam_kerja"],
                    "nama_shift": data["nama_shift"] or "Normal",
                    "durasi_menit": data["jam_per_hari"],
                    "jam_mulai": data["jam_mulai"],
                    "jam_selesai": data["jam_selesai"]
                },
                "presensi": {
                    "jam_masuk": (data["jam_masuk"].strftime("%H:%M") if data["jam_masuk"] else None),
                    "lokasi_masuk": data["lokasi_masuk"],
                    "jam_keluar": (data["jam_keluar"].strftime("%H:%M") if data["jam_keluar"] else None),
                    "lokasi_keluar": data["lokasi_keluar"],
                    "menit_terlambat": data["menit_terlambat"],
                    "istirahat": [
                        {
                            "jam_mulai": i["jam_mulai"].strftime("%H:%M") if i["jam_mulai"] else None,
                            "jam_selesai": i["jam_selesai"].strftime("%H:%M") if i["jam_selesai"] else None,
                            "durasi_menit": i["durasi_menit"],
                            "terlambat_istirahat": terlambat_istirahat,
                            "lokasi_mulai": i["lokasi_mulai"],
                            "lokasi_balik": i["lokasi_balik"]
                        }
                        for i in istirahat
                    ]
                }
            },
            message="Data absensi harian berhasil diambil"
        )



# ==================================================
# ENDPOINT CHECKIN DAN CHECKOUT PEGAWAI (ABSEN)
# ==================================================
@absensi_ns.route("/check-in")
class AbsensiCheckInResource(Resource):

    @jwt_required()
    @absensi_ns.expect(validate_parser)
    @measure_execution_time
    @log_absensi("CHECK_IN")
    def post(self):
        """(pegawai) Absensi masuk / check-in --> absen"""

        # 1️⃣ Context & Input
        id_pegawai = int(get_jwt_identity())
        args = parse_form_absensi()

        file = args["file"]
        latitude = args["latitude"]
        longitude = args["longitude"]
        id_jam_kerja = args.get("id_jam_kerja") or 1
        g.absensi_log["id_jam_kerja"] = id_jam_kerja
        # id_jam_kerja = args.get("id_jam_kerja") or 4 # default selama puasa 

        now = get_wita()
        jam_masuk = now.time()

        # 2️⃣ Validasi awal
        if is_already_checkin(id_pegawai):
            raise AbsensiError(
                "Anda sudah check-in dan belum check-out. Lakukan check-out terlebih dahulu",
                "ALREADY_CHECKED_IN",
                409
            )

        verify_wajah_absensi(id_pegawai, file)

        # 3️⃣ Validasi lokasi
        lokasi_valid = validate_lokasi_absensi(
            id_pegawai=id_pegawai,
            latitude=latitude,
            longitude=longitude
        )

        # 4️⃣ Validasi jam kerja pegawai
        if not is_valid_jam_kerja_pegawai(id_pegawai, id_jam_kerja):
            raise AbsensiError(
                "Anda tidak terdaftar pada jam kerja/shift yang dipilih",
                "SHIFT_NOT_ALLOWED",
                403
            )

        # 5️⃣ Hitung keterlambatan (pakai jam mulai shift)
        jam_kerja = get_jam_kerja_by_id(id_jam_kerja)
        if not jam_kerja:
            raise AbsensiError(
                f"Jam kerja dengan id {id_jam_kerja} tidak ditemukan",
                "SHIFT_NOT_FOUND",
                404
            )

        jam_mulai_kerja = jam_kerja["jam_mulai"]
        tanggal = get_tanggal_absensi(
            now=now,
            jam_mulai_shift=jam_mulai_kerja
        )
        menit_terlambat = hitung_menit_terlambat(
            jam_masuk=jam_masuk,
            jam_mulai_kerja=jam_mulai_kerja
        )

        # 6️⃣ Simpan absensi
        id_absensi = insert_absensi_masuk(
            id_pegawai=id_pegawai,
            tanggal=tanggal,
            jam_masuk=jam_masuk,
            id_lokasi_masuk=lokasi_valid["id_lokasi"],
            id_jam_kerja=id_jam_kerja,
            menit_terlambat=menit_terlambat
        )
        g.absensi_log["id_absensi"] = id_absensi

        # =====================================================
        # SIMPAN ISTIRAHAT OTOMATIS UNTUK SHIFT CLEANING
        # =====================================================
        if id_jam_kerja in [2, 3]:
            # Tentukan jam istirahat berdasarkan shift
            # Shift 2 (Pagi): 12:00 - 14:00
            # Shift 3 (Malam): 00:00 - 02:00
            start_time = time(12, 0) if id_jam_kerja == 2 else time(0, 0)
            end_time = time(14, 0) if id_jam_kerja == 2 else time(2, 0)
            # 1. Insert mulai istirahat
            id_istirahat = insert_istirahat_mulai(
                id_absensi=id_absensi,
                jam_mulai=start_time
            )
            # 2. Update selesai istirahat (Auto)
            update_istirahat_selesai(
                id_istirahat=id_istirahat,
                jam_selesai=end_time,
                durasi_menit=120,
                id_lokasi_balik=lokasi_valid["id_lokasi"], # Gunakan lokasi check-in awal
            )
            # 3. Akumulasi ke table utama absensi
            add_total_menit_istirahat(
                id_absensi=id_absensi,
                durasi_menit=120
            )
        # =====================================================
        
        # 7️⃣ Response
        pesan = f"Check-in berhasil pukul {jam_masuk.strftime('%H:%M')} WITA di {lokasi_valid['nama_lokasi']}"
        if menit_terlambat > 0:
            pesan += f" (terlambat {menit_terlambat} menit)"

        return success(
            message=pesan,
            data={
                "id_absensi": id_absensi,
                "jam_masuk": jam_masuk.strftime("%H:%M:%S"),
                "lokasi": lokasi_valid["nama_lokasi"],
                "id_jam_kerja": id_jam_kerja,
                "menit_terlambat": menit_terlambat
            }
        )


@absensi_ns.route("/check-out")
class AbsensiCheckoutResource(Resource):

    @jwt_required()
    @absensi_ns.expect(validate_parser)
    @measure_execution_time
    @log_absensi("CHECK_OUT")
    def put(self):
        """(pegawai) Absensi pulang / check-out --> absen"""

        # 1️⃣ Context & Input
        id_pegawai = int(get_jwt_identity())
        args = parse_form_absensi()

        file = args["file"]
        latitude = args["latitude"]
        longitude = args["longitude"]

        now = get_wita()
        tanggal = now.date()
        now_time = now.time()

        # 2️⃣ Ambil absensi untuk checkout
        absensi = get_active_absensi(id_pegawai)
        if not absensi:
            raise_absensi_tidak_aktif(id_pegawai, tanggal, "check-out")

        if absensi["jam_masuk"] is None:
            raise AbsensiError(
                "Data absensi Anda tidak memiliki jam masuk. Hubungi admin/HR",
                "INVALID_ATTENDANCE_DATA",
                409
            )

        id_absensi = absensi["id_absensi"]
        g.absensi_log["id_absensi"] = id_absensi

        # 3️⃣ Pastikan tidak ada istirahat aktif
        istirahat = get_active_istirahat(id_absensi)
        if istirahat:
            raise AbsensiError(
                f"Anda masih istirahat sejak pukul {istirahat['jam_mulai'].strftime('%H:%M')} WITA. "
                f"Selesaikan istirahat terlebih dahulu sebelum check-out",
                "BREAK_STILL_ACTIVE",
                409
            )

        # 4️⃣ Verifikasi wajah
        verify_wajah_absensi(id_pegawai, file)

        # 5️⃣ Verifikasi lokasi
        lokasi_valid = validate_lokasi_absensi(id_pegawai=id_pegawai, latitude=latitude, longitude=longitude)

        # 6️⃣ Hitung total menit kerja
        total_menit_kerja = hitung_total_menit_kerja(
            jam_masuk=absensi["jam_masuk"],
            jam_keluar=now_time,
            total_menit_istirahat=absensi["total_menit_istirahat"]
        )

        # 7️⃣ Update absensi
        update_absensi_checkout(
            id_absensi=id_absensi,
            jam_keluar=now_time,
            id_lokasi_keluar=lokasi_valid["id_lokasi"],
            total_menit_kerja=total_menit_kerja
        )
        
        # =========================
        # 🔥 AUTO LEMBUR (HARI LIBUR)
        # =========================
        if is_hari_libur(tanggal):

            # ambil jam masuk dari absensi
            jam_mulai = absensi["jam_masuk"]
            jam_selesai = now_time

            # hitung menit lembur (sementara, nanti dihitung ulang di function lembur)
            menit_lembur = int(
                (
                    datetime.combine(tanggal, jam_selesai)
                    - datetime.combine(tanggal, jam_mulai)
                ).total_seconds() / 60
            )

            insert_pengajuan_lembur(
                id_pegawai=id_pegawai,
                id_jenis_lembur=6,  # ⚠️ sesuaikan (misalnya: lembur hari libur)
                tanggal=tanggal,
                jam_mulai=jam_mulai,
                jam_selesai=jam_selesai,
                menit_lembur=menit_lembur,
                keterangan=f"Lembur otomatis dari absensi pada {tanggal.strftime('%d %B %Y')}",
                path_lampiran=None
            )

        # 8️⃣ Response
        return success(
            message=(
                f"Check-out berhasil pukul {now_time.strftime('%H:%M')} WITA di {lokasi_valid['nama_lokasi']}. "
                f"Total kerja {total_menit_kerja // 60} jam {total_menit_kerja % 60} menit"
            ),
            data={
                "jam_keluar": now_time.strftime("%H:%M:%S"),
                "lokasi": lokasi_valid["nama_lokasi"],
                "total_menit_kerja": total_menit_kerja
            }
        )



# ====================================================
# ENDPOINT ISTIRAHAT MULAI DAN SELESAI PEGAWAI (ABSEN)
# ====================================================
@absensi_ns.route("/istirahat-mulai")
class AbsensiIstirahatMulaiResource(Resource):

    @jwt_required()
    @absensi_ns.expect(validate_parser)
    @measure_execution_time
    @log_absensi("ISTIRAHAT_MULAI")
    def post(self):
        """(pegawai) Mulai istirahat --> absen"""

        # 1️⃣ Context & Input
        id_pegawai = int(get_jwt_identity())
        args = parse_form_absensi()

        file = args["file"]
        latitude = args["latitude"]
        longitude = args["longitude"]

        now = get_wita()
        now_time = now.time()

        # 2️⃣ Validasi jendela waktu (dicek duluan, sebelum proses wajah yang berat)
        #    Senin-Kamis & Sabtu-Minggu: 12:00 - 12:30, Jumat: 11:30 - 12:30
        validate_jam_istirahat(now, "mulai")

        # 3️⃣ Ambil absensi aktif (belum checkout)
        absensi = get_active_absensi(id_pegawai)
        if not absensi:
            raise_absensi_tidak_aktif(id_pegawai, now.date(), "mulai istirahat")

        id_absensi = absensi["id_absensi"]
        g.absensi_log["id_absensi"] = id_absensi

        # 4️⃣ Cek istirahat aktif
        istirahat_aktif = get_active_istirahat(id_absensi)
        if istirahat_aktif:
            raise AbsensiError(
                f"Anda sudah mulai istirahat pukul {istirahat_aktif['jam_mulai'].strftime('%H:%M')} WITA "
                f"dan belum menyelesaikannya",
                "BREAK_ALREADY_STARTED",
                409
            )

        # 5️⃣ Verifikasi wajah
        verify_wajah_absensi(id_pegawai, file)

        # 6️⃣ Verifikasi lokasi
        lokasi_valid = validate_lokasi_absensi(id_pegawai=id_pegawai, latitude=latitude, longitude=longitude)

        # 7️⃣ Simpan istirahat mulai beserta lokasinya
        id_istirahat = insert_istirahat_mulai(
            id_absensi=id_absensi,
            jam_mulai=now_time,
            id_lokasi_mulai=lokasi_valid["id_lokasi"]
        )

        # 8️⃣ Response
        return success(
            message=f"Istirahat dimulai pukul {now_time.strftime('%H:%M')} WITA di {lokasi_valid['nama_lokasi']}",
            data={
                "id_istirahat": id_istirahat,
                "jam_mulai": now_time.strftime("%H:%M:%S"),
                "lokasi": lokasi_valid["nama_lokasi"]
            }
        )


@absensi_ns.route("/istirahat-selesai")
class AbsensiIstirahatSelesaiResource(Resource):

    @jwt_required()
    @absensi_ns.expect(validate_parser)
    @measure_execution_time
    @log_absensi("ISTIRAHAT_SELESAI")
    def put(self):
        """(pegawai) Selesai istirahat --> absen"""

        # 1️⃣ Context & Input
        id_pegawai = int(get_jwt_identity())
        args = parse_form_absensi()

        file = args["file"]
        latitude = args["latitude"]
        longitude = args["longitude"]

        now = get_wita()
        now_time = now.time()

        # 2️⃣ Validasi jendela waktu: 13:30 - 14:00 (semua hari)
        validate_jam_istirahat(now, "selesai")

        # 3️⃣ Ambil absensi aktif (belum checkout)
        absensi = get_active_absensi(id_pegawai)
        if not absensi:
            raise_absensi_tidak_aktif(id_pegawai, now.date(), "menyelesaikan istirahat")

        id_absensi = absensi["id_absensi"]
        g.absensi_log["id_absensi"] = id_absensi

        # 4️⃣ Ambil istirahat aktif
        istirahat = get_active_istirahat(id_absensi)
        if not istirahat:
            raise AbsensiError(
                "Anda belum memulai istirahat atau istirahat sudah diselesaikan",
                "NO_ACTIVE_BREAK",
                409
            )

        # 5️⃣ Verifikasi wajah
        verify_wajah_absensi(id_pegawai, file)

        # 6️⃣ Verifikasi lokasi
        lokasi_valid = validate_lokasi_absensi(id_pegawai=id_pegawai, latitude=latitude, longitude=longitude)

        # 7️⃣ Hitung durasi istirahat
        durasi_menit = hitung_durasi_menit(
            istirahat["jam_mulai"],
            now_time
        )

        # 8️⃣ Tutup istirahat + akumulasi total dalam 1 transaksi
        #    (aman dari double submit: hanya berhasil jika istirahat masih aktif)
        berhasil = selesaikan_istirahat(
            id_istirahat=istirahat["id_istirahat"],
            id_absensi=id_absensi,
            jam_selesai=now_time,
            durasi_menit=durasi_menit,
            id_lokasi_balik=lokasi_valid["id_lokasi"]
        )
        if not berhasil:
            raise AbsensiError(
                "Istirahat ini sudah diselesaikan sebelumnya",
                "BREAK_ALREADY_ENDED",
                409
            )

        # 9️⃣ Response
        return success(
            message=f"Istirahat selesai pukul {now_time.strftime('%H:%M')} WITA, durasi {durasi_menit} menit",
            data={
                "jam_selesai": now_time.strftime("%H:%M:%S"),
                "durasi_menit": durasi_menit,
                "lokasi": lokasi_valid["nama_lokasi"]
            }
        )



# ====================================================
# ENDPOINT UNTUK KEPERLUAN MENU HISTORY
# ====================================================
@absensi_ns.route("/detail-basic")
class AbsensiDetailBasicResource(Resource):

    @jwt_required()
    @absensi_ns.expect(absensi_basic_parser)
    @measure_execution_time
    def get(self):
        id_pegawai = int(get_jwt_identity())
        args = absensi_basic_parser.parse_args()

        tanggal = parse_tanggal(args["tanggal"]) if args.get("tanggal") else None

        pegawai = get_pegawai_basic(id_pegawai)
        absensi = get_absensi_basic(id_pegawai, tanggal)

        if not absensi:
            return success(
                data={
                    "tanggal": tanggal.isoformat() if tanggal else None,
                    "pegawai": {
                        "id_pegawai": id_pegawai,
                        "nama_lengkap": pegawai["nama_lengkap"] if pegawai else None,
                        "nama_panggilan": pegawai["nama_panggilan"] if pegawai else None
                    },
                    "presensi": None
                },
                message="Belum ada data absensi pada tanggal ini"
            )

        istirahat = get_istirahat_absensi(absensi["id_absensi"])

        jam_selesai_terakhir = next(
            (i["jam_selesai"] for i in reversed(istirahat) if i["jam_selesai"]),
            None
        )

        terlambat_istirahat = hitung_terlambat_istirahat(jam_selesai_terakhir)

        return success(
            data={
                "tanggal": absensi["tanggal"].isoformat(),
                "pegawai": {
                    "id_pegawai": id_pegawai,
                    "nama_lengkap": pegawai["nama_lengkap"],
                    "nama_panggilan": pegawai["nama_panggilan"]
                },
                "presensi": {
                    "jam_masuk": absensi["jam_masuk"].strftime("%H:%M") if absensi["jam_masuk"] else None,
                    "lokasi_masuk": absensi["lokasi_masuk"],
                    "jam_keluar": absensi["jam_keluar"].strftime("%H:%M") if absensi["jam_keluar"] else None,
                    "lokasi_keluar": absensi["lokasi_keluar"],
                    "total_menit_kerja": absensi["total_menit_kerja"],
                    "menit_terlambat": absensi["menit_terlambat"],
                    "istirahat": [
                        {
                            "jam_mulai": i["jam_mulai"].strftime("%H:%M") if i["jam_mulai"] else None,
                            "jam_selesai": i["jam_selesai"].strftime("%H:%M") if i["jam_selesai"] else None,
                            "durasi_menit": i["durasi_menit"],
                            "terlambat_istirahat": terlambat_istirahat,
                            "lokasi_mulai": i["lokasi_mulai"],
                            "lokasi_balik": i["lokasi_balik"]
                        }
                        for i in istirahat
                    ]
                }
            },
            message="Detail absensi berhasil diambil"
        )



@absensi_ns.route("/list-basic")
class AbsensiListBasicBulananResource(Resource):

    @jwt_required()
    @absensi_ns.expect(absensi_bulanan_parser)
    @measure_execution_time
    def get(self):
        id_pegawai = int(get_jwt_identity())
        args = absensi_bulanan_parser.parse_args()

        now = get_wita()
        bulan, tahun = parse_bulan_tahun(args, now)

        # Tentukan range tanggal
        start_date = date(tahun, bulan, 1)

        last_day = monthrange(tahun, bulan)[1]
        end_date = date(tahun, bulan, last_day)

        # Jika bulan berjalan → sampai hari ini
        if bulan == now.month and tahun == now.year:
            end_date = now.date()

        pegawai = get_pegawai_basic(id_pegawai)
        absensi_map = get_absensi_bulanan(id_pegawai, start_date, end_date)
        hari_libur_set = get_hari_libur_map(start_date, end_date)

        hasil = []
        current_date = start_date

        while current_date <= end_date:
            row = absensi_map.get(current_date)

            if row:
                menit_kurang = max(
                    0,
                    row["jam_per_hari"] - (row["total_menit_kerja"] or 0)
                )

                presensi = {
                    "jam_masuk": row["jam_masuk"].strftime("%H:%M") if row["jam_masuk"] else None,
                    "jam_keluar": row["jam_keluar"].strftime("%H:%M") if row["jam_keluar"] else None,
                    "total_menit_kerja": row["total_menit_kerja"],
                    "total_menit_istirahat": row["total_menit_istirahat"],
                    "menit_terlambat": row["menit_terlambat"]
                }

                jam_kerja = {
                    "jam_mulai": row["jam_mulai"],
                    "jam_selesai": row["jam_selesai"],
                    "durasi_menit": row["jam_per_hari"]
                }
            else:
                presensi = None
                jam_kerja = {
                    "jam_mulai": "08:00",
                    "jam_selesai": "17:00",
                    "durasi_menit": 480
                }

            is_minggu = current_date.weekday() == 6  # 6 = Minggu
            is_libur = current_date in hari_libur_set

            if is_libur:
                keterangan_hari = "Hari Libur"
            elif is_minggu:
                keterangan_hari = "Hari Minggu"
            else:
                keterangan_hari = "Hari Kerja"

            hasil.append({
                "tanggal": current_date.isoformat(),
                "hari": {
                    "is_minggu": is_minggu,
                    "is_libur": is_libur,
                    "keterangan": keterangan_hari
                },
                "jam_kerja": jam_kerja,
                "presensi": presensi
            })

            current_date += timedelta(days=1)

        return success(
            data={
                "bulan": f"{tahun}-{str(bulan).zfill(2)}",
                "pegawai": {
                    "id_pegawai": id_pegawai,
                    "nama_lengkap": pegawai["nama_lengkap"],
                    "nama_panggilan": pegawai["nama_panggilan"]
                },
                "kehadiran": hasil
            },
            message="Daftar kehadiran bulanan berhasil diambil"
        )


def hitung_hari_kerja_efektif(start_date, end_date):
    hari_libur = get_hari_libur_map(start_date, end_date)

    total = 0
    current = start_date

    while current <= end_date:
        # weekday(): Senin=0 ... Minggu=6
        if current.weekday() != 6 and current not in hari_libur:
            total += 1
        current += timedelta(days=1)

    return total

@absensi_ns.route("/rekap-basic")
class AbsensiRekapBasicBulananResource(Resource):

    @jwt_required()
    @absensi_ns.expect(absensi_bulanan_parser)
    @measure_execution_time
    def get(self):
        """(pegawai) Rekap absensi bulanan"""

        id_pegawai = int(get_jwt_identity())
        args = absensi_bulanan_parser.parse_args()

        now = get_wita()
        bulan, tahun = parse_bulan_tahun(args, now)

        start_date = date(tahun, bulan, 1)
        last_day = monthrange(tahun, bulan)[1]
        end_date = date(tahun, bulan, last_day)

        # bulan berjalan → sampai hari ini
        if bulan == now.month and tahun == now.year:
            end_date = now.date()

        pegawai = get_pegawai_basic(id_pegawai)
        rekap = get_rekap_basic_absensi_bulanan(id_pegawai, start_date, end_date)

        hari_kerja_efektif = hitung_hari_kerja_efektif(start_date, end_date)

        total_hadir = rekap["total_hadir"] or 0
        total_izin = 0   # dummy
        total_sakit = 0  # dummy

        total_alpha = max(
            0,
            hari_kerja_efektif - total_hadir - total_izin - total_sakit
        )

        return success(
            data={
                "bulan": f"{tahun}-{str(bulan).zfill(2)}",
                "pegawai": {
                    "id_pegawai": id_pegawai,
                    "nama_lengkap": pegawai["nama_lengkap"]
                },
                "rekap": {
                    "hadir": total_hadir,
                    "izin": total_izin,
                    "sakit": total_sakit,
                    "alpha": total_alpha,
                    "total_menit_kerja": rekap["total_menit_kerja"],
                    "total_menit_terlambat": rekap["total_menit_terlambat"]
                }
            },
            message="Rekap absensi bulanan berhasil diambil"
        )



# ====================================================
# ENDPOINT LOG ERROR ABSENSI (ADMIN)
# ====================================================
AKSI_LOG = ("CHECK_IN", "CHECK_OUT", "ISTIRAHAT_MULAI", "ISTIRAHAT_SELESAI")

absensi_log_parser = reqparse.RequestParser()
absensi_log_parser.add_argument("tanggal_mulai", type=str, location="args", help="YYYY-MM-DD (default: 7 hari terakhir)")
absensi_log_parser.add_argument("tanggal_selesai", type=str, location="args", help="YYYY-MM-DD (default: hari ini)")
absensi_log_parser.add_argument("id_pegawai", type=int, location="args")
absensi_log_parser.add_argument("id_departemen", type=int, location="args")
absensi_log_parser.add_argument("aksi", type=str, location="args", help="CHECK_IN | CHECK_OUT | ISTIRAHAT_MULAI | ISTIRAHAT_SELESAI")
absensi_log_parser.add_argument("error_code", type=str, location="args", help="mis. FACE_MISMATCH, OUTSIDE_RADIUS")
absensi_log_parser.add_argument("http_status", type=int, location="args", help="mis. 409, 422, 500")
absensi_log_parser.add_argument("search", type=str, location="args", help="Cari nama, NIP, atau isi pesan")
absensi_log_parser.add_argument("page", type=int, location="args", default=1)
absensi_log_parser.add_argument("limit", type=int, location="args", default=20, help="Maks 100")


def parse_filter_log(args, now):
    tanggal_selesai = parse_tanggal(args["tanggal_selesai"]) if args.get("tanggal_selesai") else now.date()
    tanggal_mulai = (
        parse_tanggal(args["tanggal_mulai"]) if args.get("tanggal_mulai")
        else tanggal_selesai - timedelta(days=6)
    )
    if tanggal_mulai > tanggal_selesai:
        raise AbsensiError("tanggal_mulai tidak boleh setelah tanggal_selesai", "INVALID_DATE_RANGE", 400)

    aksi = args["aksi"].upper() if args.get("aksi") else None
    if aksi and aksi not in AKSI_LOG:
        raise AbsensiError(
            f"Aksi '{args['aksi']}' tidak valid. Pilihan: {', '.join(AKSI_LOG)}",
            "INVALID_ACTION",
            400
        )

    return {
        "tanggal_mulai": tanggal_mulai,
        "tanggal_selesai": tanggal_selesai,
        "id_pegawai": args.get("id_pegawai"),
        "id_departemen": args.get("id_departemen"),
        "aksi": aksi,
        "error_code": args["error_code"].upper() if args.get("error_code") else None,
        "http_status": args.get("http_status"),
        "berhasil": False,
        "search": args.get("search"),
    }


@absensi_ns.route("/log")
class AbsensiLogListResource(Resource):

    @jwt_required()
    @role_required("admin")
    @absensi_ns.expect(absensi_log_parser)
    @measure_execution_time
    def get(self):
        """(admin) List log error absensi pegawai"""
        args = absensi_log_parser.parse_args()
        filters = parse_filter_log(args, get_wita())

        page = max(args.get("page") or 1, 1)
        limit = min(max(args.get("limit") or 20, 1), 100)

        rows, total = get_absensi_log_list(filters, page, limit)

        return success(
            data=[
                {
                    "id_log": r["id_log"],
                    "waktu": r["created_at"],
                    "aksi": r["aksi"],
                    "http_status": r["http_status"],
                    "error_code": r["error_code"],
                    "message": r["message"],
                    "errors": r["errors"],
                    "pegawai": {
                        "id_pegawai": r["id_pegawai"],
                        "nip": r["nip"],
                        "nama_lengkap": r["nama_lengkap"],
                        "nama_panggilan": r["nama_panggilan"],
                        "departemen": r["nama_departemen"]
                    },
                    "latitude": float(r["latitude"]) if r["latitude"] is not None else None,
                    "longitude": float(r["longitude"]) if r["longitude"] is not None else None,
                    "id_absensi": r["id_absensi"],
                    "id_jam_kerja": r["id_jam_kerja"],
                    "durasi_ms": r["durasi_ms"],
                    "ada_detail_teknis": r["ada_detail_teknis"]
                }
                for r in rows
            ],
            message=f"Ditemukan {total} log error absensi" if total else "Tidak ada log error absensi pada filter ini",
            meta={
                "page": page,
                "limit": limit,
                "total": total,
                "total_page": (total + limit - 1) // limit,
                "filter": {k: str(v) if isinstance(v, date) else v for k, v in filters.items() if v is not None}
            }
        )


@absensi_ns.route("/log/ringkasan")
class AbsensiLogRingkasanResource(Resource):

    @jwt_required()
    @role_required("admin")
    @absensi_ns.expect(absensi_log_parser)
    @measure_execution_time
    def get(self):
        """(admin) Ringkasan log error absensi per error_code, aksi, dan pegawai"""
        args = absensi_log_parser.parse_args()
        filters = parse_filter_log(args, get_wita())

        ringkasan = get_absensi_log_ringkasan(filters)

        return success(
            data={
                "total_error": sum(r["jumlah"] for r in ringkasan["per_error_code"]),
                "per_error_code": [dict(r) for r in ringkasan["per_error_code"]],
                "per_aksi": [dict(r) for r in ringkasan["per_aksi"]],
                "top_pegawai": [dict(r) for r in ringkasan["top_pegawai"]],
            },
            message="Ringkasan log error absensi berhasil diambil",
            meta={"filter": {k: str(v) if isinstance(v, date) else v for k, v in filters.items() if v is not None}}
        )


@absensi_ns.route("/log/<int:id_log>")
class AbsensiLogDetailResource(Resource):

    @jwt_required()
    @role_required("admin")
    @measure_execution_time
    def get(self, id_log):
        """(admin) Detail satu log error absensi, termasuk detail teknis (traceback)"""
        log = get_absensi_log_by_id(id_log)
        if not log:
            raise AbsensiError(f"Log dengan id {id_log} tidak ditemukan", "LOG_NOT_FOUND", 404)

        data = dict(log)
        data["latitude"] = float(log["latitude"]) if log["latitude"] is not None else None
        data["longitude"] = float(log["longitude"]) if log["longitude"] is not None else None

        return success(data=data, message="Detail log error absensi berhasil diambil")
