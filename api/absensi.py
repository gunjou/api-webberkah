from calendar import monthrange
import os
from dotenv import load_dotenv
from flask_restx import Namespace, Resource
from flask import request
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import date, datetime, time, timedelta
from flask_restx import reqparse
from werkzeug.datastructures import FileStorage

from api.shared.exceptions import ValidationError
from api.shared.helper import count_hari_dalam_bulan, get_wita
from api.shared.response import success
from api.utils.decorator import measure_execution_time
from api.query.q_absensi import *
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
# FUNGSI HELPER UNTUK VALIDASI LOKASI
# ==================================================
def validate_lokasi_absensi(id_pegawai: int, latitude: float, longitude: float) -> dict:
    """
    Validasi lokasi absensi:
    - Lokasi fisik → radius + akses pegawai
    - Jika gagal → cek WFH
    """

    # 1️⃣ Ambil semua lokasi aktif
    all_lokasi = get_all_lokasi_absensi()

    lokasi_valid = find_valid_lokasi(latitude=latitude, longitude=longitude, lokasi_list=all_lokasi)

    # 2️⃣ Jika lokasi fisik TIDAK valid → cek WFH
    if not lokasi_valid:
        if is_pegawai_wfh(id_pegawai):
            return {
                "id_lokasi": os.getenv("ID_LOKASI_WFH"),
                "nama_lokasi": "WFH",
                "is_wfh": True
            }
        raise ValidationError("Anda tidak berada di lokasi absensi yang diizinkan")

    # 3️⃣ Lokasi fisik valid → cek akses pegawai
    allowed_lokasi_ids = get_allowed_lokasi_ids_pegawai(id_pegawai)

    if lokasi_valid["id_lokasi"] not in allowed_lokasi_ids:
        raise ValidationError(
            f"Anda berada di {lokasi_valid['nama_lokasi']}, "
            "namun tidak terdaftar di lokasi tersebut"
        )

    lokasi_valid["is_wfh"] = False
    return lokasi_valid

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
                tanggal = datetime.strptime(tanggal_str, "%Y-%m-%d").date()
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
                message="Belum ada data absensi"
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
                            "jam_mulai": i["jam_mulai"].strftime("%H:%M"),
                            "jam_selesai": i["jam_selesai"].strftime("%H:%M") if i["jam_selesai"] else None,
                            "durasi_menit": i["durasi_menit"],
                            "terlambat_istirahat": terlambat_istirahat,
                            "lokasi_balik": i["lokasi_balik"]
                        }
                        for i in istirahat
                    ]
                }
            },
            message="Data absensi harian"
        )



# ==================================================
# ENDPOINT CHECKIN DAN CHECKOUT PEGAWAI (ABSEN)
# ==================================================
@absensi_ns.route("/check-in")
class AbsensiCheckInResource(Resource):

    @jwt_required()
    @absensi_ns.expect(validate_parser)
    @measure_execution_time
    def post(self):
        """(pegawai) Absensi masuk / check-in --> absen"""

        # 1️⃣ Context & Input
        id_pegawai = int(get_jwt_identity())
        args = validate_parser.parse_args()

        file = args["file"]
        latitude = args["latitude"]
        longitude = args["longitude"]
        id_jam_kerja = args.get("id_jam_kerja") or 1

        now = get_wita()
        jam_masuk = now.time()

        # 2️⃣ Validasi awal
        if is_already_checkin(id_pegawai):
            raise ValidationError("Anda masih memiliki absensi aktif")

        if not verify_face(id_pegawai, file):
            raise ValidationError("Wajah tidak cocok dengan data pegawai")

        # 3️⃣ Validasi lokasi
        lokasi_valid = validate_lokasi_absensi(
            id_pegawai=id_pegawai,
            latitude=latitude,
            longitude=longitude
        )

        # 4️⃣ Validasi jam kerja pegawai
        if not is_valid_jam_kerja_pegawai(id_pegawai, id_jam_kerja):
            raise ValidationError("Anda tidak diperbolehkan mengambil jam kerja ini")

        # 5️⃣ Hitung keterlambatan (pakai jam mulai shift)
        jam_kerja = get_jam_kerja_by_id(id_jam_kerja)
        if not jam_kerja:
            raise ValidationError("Jam kerja tidak valid")

        jam_mulai_kerja = jam_kerja["jam_mulai"]
        tanggal = get_tanggal_absensi(
            now=now,
            jam_mulai_shift=jam_mulai_kerja
        )
        print(tanggal)
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
        return success(
            message="Absensi masuk berhasil",
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
    def put(self):
        """(pegawai) Absensi pulang / check-out --> absen"""

        # 1️⃣ Context & Input
        id_pegawai = int(get_jwt_identity())
        args = validate_parser.parse_args()

        file = args["file"]
        latitude = args["latitude"]
        longitude = args["longitude"]

        now = get_wita()
        tanggal = now.date()
        now_time = now.time()

        # 2️⃣ Ambil absensi untuk checkout
        absensi = get_active_absensi(id_pegawai)
        if not absensi:
            raise ValidationError("Anda belum melakukan absensi masuk")

        if absensi["jam_masuk"] is None:
            raise ValidationError("Data absensi tidak valid")

        id_absensi = absensi["id_absensi"]

        # 3️⃣ Pastikan tidak ada istirahat aktif
        istirahat = get_active_istirahat(id_absensi)
        if istirahat:
            raise ValidationError("Selesaikan istirahat terlebih dahulu")

        # 4️⃣ Verifikasi wajah
        if not verify_face(id_pegawai, file):
            raise ValidationError("Wajah tidak cocok")

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

        # 8️⃣ Response
        return success(
            message="Check-out berhasil",
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
    @measure_execution_time
    def post(self):
        """(pegawai) Mulai istirahat --> absen"""
        id_pegawai = int(get_jwt_identity())
        tanggal = get_wita().date()
        now_time = get_wita().time()

        # 1️⃣ ambil absensi hari ini
        absensi = get_absensi_hari_ini(id_pegawai, tanggal)
        if not absensi:
            raise ValidationError("Anda belum melakukan absensi masuk hari ini")

        if absensi["jam_keluar"] is not None:
            raise ValidationError("Absensi hari ini sudah ditutup")

        id_absensi = absensi["id_absensi"]

        # 2️⃣ validasi waktu minimal istirahat (>= 11:30)
        if now_time < time(11, 30):
            raise ValidationError(
                "Istirahat hanya dapat dimulai setelah pukul 11:30"
            )

        # 3️⃣ cek istirahat aktif
        istirahat = get_active_istirahat(id_absensi)
        if istirahat:
            raise ValidationError("Selesaikan istirahat terlebih dahulu")

        # 4️⃣ insert istirahat mulai
        id_istirahat = insert_istirahat_mulai(
            id_absensi=id_absensi,
            jam_mulai=now_time
        )

        return success(
            data={
                "id_istirahat": id_istirahat,
                "jam_mulai": now_time.strftime("%H:%M:%S")
            },
            message="Istirahat dimulai"
        )


@absensi_ns.route("/istirahat-selesai")
class AbsensiIstirahatSelesaiResource(Resource):

    @jwt_required()
    @absensi_ns.expect(validate_parser)
    @measure_execution_time
    def put(self):
        """(pegawai) Selesai istirahat --> absen"""

        # 1️⃣ Context & Input
        id_pegawai = int(get_jwt_identity())
        args = validate_parser.parse_args()

        file = args["file"]
        latitude = args["latitude"]
        longitude = args["longitude"]

        now = get_wita()
        tanggal = now.date()
        now_time = now.time()

        # 2️⃣ Ambil absensi hari ini
        absensi = get_absensi_hari_ini(id_pegawai, tanggal)
        if not absensi:
            raise ValidationError("Anda belum melakukan absensi masuk")

        if absensi["jam_keluar"] is not None:
            raise ValidationError("Absensi hari ini sudah ditutup")

        id_absensi = absensi["id_absensi"]

        # 3️⃣ Ambil istirahat aktif
        istirahat = get_active_istirahat(id_absensi)
        if not istirahat:
            raise ValidationError("Tidak ada istirahat aktif")

        # 4️⃣ Verifikasi wajah
        if not verify_face(id_pegawai, file):
            raise ValidationError("Wajah tidak cocok")

        # 5️⃣ Verifikasi lokasi
        lokasi_valid = validate_lokasi_absensi(id_pegawai=id_pegawai, latitude=latitude, longitude=longitude)


        # 6️⃣ Hitung durasi istirahat
        durasi_menit = hitung_durasi_menit(
            istirahat["jam_mulai"],
            now_time
        )

        # 7️⃣ Update istirahat & total menit istirahat
        update_istirahat_selesai(
            id_istirahat=istirahat["id_istirahat"],
            jam_selesai=now_time,
            durasi_menit=durasi_menit,
            id_lokasi_balik=lokasi_valid["id_lokasi"],
        )

        add_total_menit_istirahat(
            id_absensi=id_absensi,
            durasi_menit=durasi_menit
        )

        # 8️⃣ Response
        return success(
            message="Istirahat selesai",
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

        tanggal = (
            datetime.strptime(args["tanggal"], "%Y-%m-%d").date()
            if args.get("tanggal") else None
        )

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
                message="Belum ada data absensi"
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
                            "jam_mulai": i["jam_mulai"].strftime("%H:%M"),
                            "jam_selesai": i["jam_selesai"].strftime("%H:%M") if i["jam_selesai"] else None,
                            "durasi_menit": i["durasi_menit"],
                            "terlambat_istirahat": terlambat_istirahat,
                            "lokasi_balik": i["lokasi_balik"]
                        }
                        for i in istirahat
                    ]
                }
            },
            message="Detail absensi"
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
        bulan = args.get("bulan") or now.month
        tahun = args.get("tahun") or now.year

        # Tentukan range tanggal
        start_date = date(tahun, bulan, 1)

        last_day = monthrange(tahun, bulan)[1]
        end_date = date(tahun, bulan, last_day)

        # Jika bulan berjalan → sampai hari ini
        if bulan == now.month and tahun == now.year:
            end_date = now.date()

        pegawai = get_pegawai_basic(id_pegawai)
        absensi_map = get_absensi_bulanan(id_pegawai, start_date, end_date)

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

            hasil.append({
                "tanggal": current_date.isoformat(),
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
            message="List kehadiran bulanan"
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
        bulan = args.get("bulan") or now.month
        tahun = args.get("tahun") or now.year

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
            message="Rekap absensi bulanan"
        )
