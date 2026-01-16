from flask_restx import Namespace, Resource, reqparse
from flask_jwt_extended import jwt_required
from datetime import datetime

from api.query.q_master import get_jam_kerja_by_id
from api.shared.response import success
from api.shared.exceptions import ValidationError
from api.utils.decorator import measure_execution_time, role_required
from api.shared.helper import get_wita
from api.query.q_presensi import *


presensi_ns = Namespace("presensi", description="Manajemen Presensi (Admin)")


# ======================================================================
# SWAGGER PARSER
# ======================================================================
presensi_parser = reqparse.RequestParser()
presensi_parser.add_argument("tanggal", type=str, required=False, help="Filter tanggal (YYYY-MM-DD)")
presensi_parser.add_argument("id_departemen", type=int, required=False, help="Filter departemen")
presensi_parser.add_argument("id_status_pegawai", type=int, required=False, help="Filter status pegawai")

update_presensi_parser = reqparse.RequestParser()
update_presensi_parser.add_argument("jam_masuk", type=str, required=False, help="HH:MM")
update_presensi_parser.add_argument("jam_keluar", type=str, required=False, help="HH:MM")
update_presensi_parser.add_argument("id_lokasi_masuk", type=int, required=False)
update_presensi_parser.add_argument("id_lokasi_keluar", type=int, required=False)
update_presensi_parser.add_argument("istirahat_mulai", type=str, required=False, help="HH:MM")
update_presensi_parser.add_argument("istirahat_selesai", type=str, required=False, help="HH:MM")
update_presensi_parser.add_argument("id_lokasi_istirahat", type=int, required=False)

manual_presensi_parser = reqparse.RequestParser()
manual_presensi_parser.add_argument("tanggal", type=str, required=True)
manual_presensi_parser.add_argument("id_pegawai", type=int, required=True)
manual_presensi_parser.add_argument("id_jam_kerja", type=int, required=False, default=1)
manual_presensi_parser.add_argument("jam_masuk", type=str, required=True)
manual_presensi_parser.add_argument("id_lokasi_masuk", type=int, required=True)
manual_presensi_parser.add_argument("jam_keluar", type=str, required=False)
manual_presensi_parser.add_argument("id_lokasi_keluar", type=int, required=False)
manual_presensi_parser.add_argument("istirahat_mulai", type=str, required=False)
manual_presensi_parser.add_argument("istirahat_selesai", type=str, required=False)
manual_presensi_parser.add_argument("id_lokasi_istirahat", type=int, required=False)


# ======================================================================
# HELPER FUNCTION
# ======================================================================
def parse_time(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%H:%M").time()
    except ValueError:
        raise ValidationError("Format waktu harus HH:MM")



# ======================================================================
# ENDPOINT GET DATA PRESENSI HARIAN SEMUA PEGAWAI (ADMIN.WEBBERKAH)
# ======================================================================
@presensi_ns.route("")
class PresensiAdminListResource(Resource):

    @jwt_required()
    @role_required("admin")
    @presensi_ns.expect(presensi_parser)
    @measure_execution_time
    def get(self):
        """(admin) List presensi semua pegawai (harian)"""

        args = presensi_parser.parse_args()

        # tanggal default hari ini
        if args.get("tanggal"):
            try:
                tanggal = datetime.strptime(
                    args["tanggal"], "%Y-%m-%d"
                ).date()
            except ValueError:
                raise ValidationError("Format tanggal harus YYYY-MM-DD")
        else:
            tanggal = get_wita().date()

        id_departemen = args.get("id_departemen")
        id_status_pegawai = args.get("id_status_pegawai")

        rows = get_admin_presensi_harian(
            tanggal=tanggal,
            id_departemen=id_departemen,
            id_status_pegawai=id_status_pegawai
        )

        return success(
            message="Data presensi pegawai",
            data=[
                {
                    "tanggal": r["tanggal"].isoformat(),

                    "pegawai": {
                        "id_pegawai": r["id_pegawai"],
                        "nip": r["nip"],
                        "nama_lengkap": r["nama_lengkap"],
                        "nama_panggilan": r["nama_panggilan"],
                        "id_status_pegawai": r["id_status_pegawai"],
                        "status_pegawai": r["status_pegawai"],
                        "id_departemen": r["id_departemen"],
                        "nama_departemen": r["nama_departemen"],
                    },

                    "jam_kerja": {
                        "id_jam_kerja": r["id_jam_kerja"],
                        "nama_shift": r["nama_shift"],
                        "jam_mulai": r["jam_mulai_shift"],
                        "jam_selesai": r["jam_selesai_shift"],
                    },

                    "presensi": {
                        "id_absensi": r["id_absensi"],
                        "jam_masuk": (
                            r["jam_checkin"].strftime("%H:%M")
                            if r["jam_checkin"] else None
                        ),
                        "jam_keluar": (
                            r["jam_checkout"].strftime("%H:%M")
                            if r["jam_checkout"] else None
                        ),
                        "id_lokasi_masuk": r["id_lokasi_masuk"],
                        "lokasi_masuk": r["lokasi_checkin"],
                        "id_lokasi_keluar": r["id_lokasi_keluar"],
                        "lokasi_keluar": r["lokasi_checkout"],
                        "menit_terlambat": r["menit_terlambat"],
                        "istirahat": {
                            "id_lokasi_istirahat": r["id_lokasi_balik"],
                            "jam_mulai": (
                                r["jam_mulai_istirahat"].strftime("%H:%M")
                                if r["jam_mulai_istirahat"] else None
                            ),
                            "jam_selesai": (
                                r["jam_selesai_istirahat"].strftime("%H:%M")
                                if r["jam_selesai_istirahat"] else None
                            )
                        }
                    }
                }
                for r in rows
            ],
            meta={
                "tanggal": tanggal.isoformat(),
                "total": len(rows)
            }
        )



# ======================================================================
# ENDPOINT UPDATE DAN DELETE PRESENSI PEGAWAI BY ID (ADMIN.WEBBERKAH)
# ======================================================================
@presensi_ns.route("/<int:id_absensi>")
class PresensiUpdateResource(Resource):

    @jwt_required()
    @role_required("admin")
    @presensi_ns.expect(update_presensi_parser)
    @measure_execution_time
    def put(self, id_absensi):
        """(admin) Update presensi pegawai"""

        args = update_presensi_parser.parse_args()

        # pastikan absensi ada
        absensi = get_absensi_by_id(id_absensi)
        if not absensi:
            raise ValidationError("Data absensi tidak ditemukan")

        update_absensi_manual(
            id_absensi=id_absensi,
            jam_masuk=args.get("jam_masuk"),
            jam_keluar=args.get("jam_keluar"),
            id_lokasi_masuk=args.get("id_lokasi_masuk"),
            id_lokasi_keluar=args.get("id_lokasi_keluar"),
        )

        upsert_absensi_istirahat(
            id_absensi=id_absensi,
            jam_mulai=args.get("istirahat_mulai"),
            jam_selesai=args.get("istirahat_selesai"),
            id_lokasi_balik=args.get("id_lokasi_istirahat")
        )

        recalc_absensi(id_absensi)

        return success(message="Presensi berhasil diperbarui")
    
    
    @jwt_required()
    @role_required("admin")
    @measure_execution_time
    def delete(self, id_absensi):
        """(admin) Soft delete presensi pegawai"""

        absensi = get_absensi_by_id(id_absensi)
        if not absensi:
            raise ValidationError("Data presensi tidak ditemukan")

        soft_delete_presensi(id_absensi)

        return success(
            message="Presensi berhasil dihapus (soft delete)"
        )



# ======================================================================
# ENDPOINT ADD PRESENSI PEGAWAI BY ID OLEH ADMIN (ADMIN.WEBBERKAH)
# ======================================================================
@presensi_ns.route("/manual")
class PresensiManualCreateResource(Resource):

    @jwt_required()
    @role_required("admin")
    @presensi_ns.expect(manual_presensi_parser)
    @measure_execution_time
    def post(self):
        """(admin) Tambah presensi manual pegawai"""

        args = manual_presensi_parser.parse_args()

        try:
            tanggal = datetime.strptime(args["tanggal"], "%Y-%m-%d").date()
            jam_masuk = datetime.strptime(args["jam_masuk"], "%H:%M").time()
            jam_keluar = (
                datetime.strptime(args["jam_keluar"], "%H:%M").time()
                if args.get("jam_keluar") else None
            )
            ist_mulai = (
                datetime.strptime(args["istirahat_mulai"], "%H:%M").time()
                if args.get("istirahat_mulai") else None
            )
            ist_selesai = (
                datetime.strptime(args["istirahat_selesai"], "%H:%M").time()
                if args.get("istirahat_selesai") else None
            )
        except ValueError:
            raise ValidationError("Format jam harus HH:MM")

        # 1️⃣ Validasi pegawai
        if not is_pegawai_active(args["id_pegawai"]):
            raise ValidationError("Pegawai tidak ditemukan atau tidak aktif")

        # 2️⃣ Cek absensi existing
        if is_absensi_exist(args["id_pegawai"], tanggal):
            raise ValidationError("Absensi pada tanggal ini sudah ada")

        # 3️⃣ Ambil jam kerja
        jam_kerja = get_jam_kerja_by_id(args["id_jam_kerja"])
        if not jam_kerja:
            raise ValidationError("Jam kerja tidak valid")

        menit_terlambat = hitung_menit_terlambat(
            jam_masuk,
            jam_kerja["jam_mulai"]
        )

        # 4️⃣ INSERT absensi
        id_absensi = insert_absensi_manual(
            id_pegawai=args["id_pegawai"],
            tanggal=tanggal,
            id_jam_kerja=args["id_jam_kerja"],
            jam_masuk=jam_masuk,
            jam_keluar=jam_keluar,
            id_lokasi_masuk=args["id_lokasi_masuk"],
            id_lokasi_keluar=args.get("id_lokasi_keluar"),
            menit_terlambat=menit_terlambat
        )

        # 5️⃣ UPSERT istirahat (opsional)
        if ist_mulai or ist_selesai:
            upsert_absensi_istirahat(
                id_absensi=id_absensi,
                jam_mulai=ist_mulai,
                jam_selesai=ist_selesai,
                id_lokasi_balik=args.get("id_lokasi_istirahat")
            )

        # 6️⃣ Recalculate
        recalc_absensi(id_absensi)

        return success(
            message="Presensi manual berhasil ditambahkan",
            data={"id_absensi": id_absensi}
        )
