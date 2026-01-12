from flask_restx import Namespace, Resource
from flask import request
from flask_jwt_extended import jwt_required, get_jwt_identity
from datetime import datetime, time
from flask_restx import reqparse
from werkzeug.datastructures import FileStorage

from api.shared.exceptions import ValidationError
from api.shared.helper import get_wita
from api.shared.response import success
from api.utils.decorator import measure_execution_time
from api.query.q_absensi import *
from api.utils.face import verify_face
from api.utils.geo import find_valid_lokasi
from api.utils.time_calc import *

absensi_ns = Namespace("absensi", description="Absensi Pegawai")

validate_parser = reqparse.RequestParser()
validate_parser.add_argument("file", type=FileStorage, location="files", required=True, help="Foto wajah pegawai")
validate_parser.add_argument("latitude", type=float, location="form", required=True, help="Latitude lokasi absensi")
validate_parser.add_argument("longitude", type=float, location="form", required=True, help="Longitude lokasi absensi")



# ==================================================
# FUNGSI HELPER UNTUK VALIDASI LOKASI
# ==================================================
def validate_lokasi_absensi(id_pegawai: int, latitude: float, longitude: float) -> dict:
    """
    Validasi lokasi absensi dengan alur:
    1. Lokasi fisik valid (radius & koordinat)
    2. Pegawai memiliki akses ke lokasi tersebut
    """

    # 1️⃣ Validasi lokasi fisik
    all_lokasi = get_all_lokasi_absensi()
    lokasi_valid = find_valid_lokasi(latitude, longitude, all_lokasi)

    if not lokasi_valid:
        raise ValidationError("Lokasi tidak valid untuk absensi")

    # 2️⃣ Validasi akses pegawai ke lokasi
    allowed_lokasi_ids = get_allowed_lokasi_ids_pegawai(id_pegawai)

    if lokasi_valid["id_lokasi"] not in allowed_lokasi_ids:
        raise ValidationError(
            f"Anda berada di {lokasi_valid['nama_lokasi']}, "
            "namun tidak terdaftar di lokasi tersebut"
        )

    return lokasi_valid



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

        # ambil tanggal dari query param
        tanggal_str = request.args.get("tanggal")
        if tanggal_str:
            tanggal = datetime.strptime(tanggal_str, "%Y-%m-%d").date()
        else:
            tanggal = get_wita().date()

        data = get_absensi_harian(
            id_pegawai=id_pegawai,
            tanggal=tanggal
        )

        # jika belum ada absensi sama sekali
        if not data or not data["id_absensi"]:
            return success(
                data={
                    "pegawai": {
                        "id_pegawai": id_pegawai,
                        "nama_lengkap": data["nama_lengkap"] if data else None,
                        "nama_panggilan": data["nama_panggilan"] if data else None
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
                },
                "jam_kerja": {
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

        now = get_wita()
        tanggal = now.date()
        jam_masuk = now.time()

        # 2️⃣ Validasi awal
        if is_already_checkin(id_pegawai, tanggal):
            raise ValidationError("Anda sudah melakukan absensi masuk hari ini")

        if not verify_face(id_pegawai, file):
            raise ValidationError("Wajah tidak cocok dengan data pegawai")

        # 3️⃣ Validasi lokasi
        lokasi_valid = validate_lokasi_absensi(id_pegawai=id_pegawai, latitude=latitude, longitude=longitude)

        # 4️⃣ Hitung jam kerja & keterlambatan
        id_jam_kerja = 1  # ⬅️ default (siap dikembangkan ke shift)
        menit_terlambat = hitung_menit_terlambat(
            jam_masuk=jam_masuk,
            jam_mulai_kerja=time(8, 0)
        )

        # 5️⃣ Simpan absensi
        id_absensi = insert_absensi_masuk(
            id_pegawai=id_pegawai,
            tanggal=tanggal,
            jam_masuk=jam_masuk,
            id_lokasi_masuk=lokasi_valid["id_lokasi"],
            id_jam_kerja=id_jam_kerja,
            menit_terlambat=menit_terlambat
        )

        # 6️⃣ Response
        return success(
            message="Absensi masuk berhasil",
            data={
                "id_absensi": id_absensi,
                "jam_masuk": jam_masuk.strftime("%H:%M:%S"),
                "lokasi": lokasi_valid["nama_lokasi"],
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
        absensi = get_absensi_for_checkout(id_pegawai, tanggal)
        if not absensi:
            raise ValidationError("Anda belum melakukan absensi masuk")

        if absensi["jam_keluar"] is not None:
            raise ValidationError("Anda sudah melakukan check-out")

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

