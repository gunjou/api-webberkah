from flask_restx import Namespace, Resource, reqparse
from flask import request
from calendar import monthrange
from flask_jwt_extended import get_jwt, jwt_required, get_jwt_identity
from werkzeug.datastructures import FileStorage
from datetime import date, datetime, timedelta

from api.shared.response import success
from api.shared.exceptions import ValidationError
from api.utils.decorator import measure_execution_time, role_required
from api.utils.uploader import upload_lampiran_izin_to_cdn
from api.query.q_perizinan import *


perizinan_ns = Namespace("perizinan", description="Pengajuan Izin Pegawai")


# ======================================================================
# PARSER ENDPOINT PERIZINAN
# ======================================================================
izin_aktif = reqparse.RequestParser()
izin_aktif.add_argument("tanggal", type=str, required=False, location="args", help="Tanggal izin (YYYY-MM-DD)")

izin_parser = reqparse.RequestParser()
izin_parser.add_argument("id_jenis_izin", type=int, required=True, location="form", help="Jenis izin wajib diisi")
izin_parser.add_argument("tanggal_mulai", type=str, required=True, location="form", help="Tanggal mulai izin (YYYY-MM-DD)")
izin_parser.add_argument("tanggal_selesai", type=str, required=True, location="form", help="Tanggal selesai izin (YYYY-MM-DD)")
izin_parser.add_argument("alasan", type=str, required=True, location="form", help="Alasan izin")
izin_parser.add_argument("lampiran", type=FileStorage, required=True, location="files")

izin_history_parser = reqparse.RequestParser()
izin_history_parser.add_argument("bulan", type=int, required=False, location="args", help="Bulan (1-12)")
izin_history_parser.add_argument("tahun", type=int, required=False, location="args", help="Tahun (YYYY)")

izin_list_parser = reqparse.RequestParser()
izin_list_parser.add_argument("bulan", type=int, required=False, help="Bulan (1-12), default bulan berjalan")
izin_list_parser.add_argument("tahun", type=int, required=False, help="Tahun, default tahun berjalan")
izin_list_parser.add_argument("status_approval", type=str, required=False, choices=["pending", "approved", "rejected"], help="Status approval izin")
izin_list_parser.add_argument("id_departemen", type=int, required=False, help="Filter berdasarkan departemen")
izin_list_parser.add_argument("id_status_pegawai", type=int, required=False, help="Filter berdasarkan status pegawai")
izin_list_parser.add_argument("id_pegawai", type=int, required=False, help="Filter berdasarkan pegawai tertentu")
izin_list_parser.add_argument("kategori_izin", type=str, required=False, choices=["IZIN", "SAKIT", "CUTI"], help="Kategori izin: IZIN | SAKIT | CUTI")

izin_reject_parser = reqparse.RequestParser()
izin_reject_parser.add_argument("alasan_penolakan", type=str, required=True, help="Alasan penolakan perizinan")



# ======================================================================
# ENDPOINT PENGAJUAN IZIN OLEH PEGAWAI (PEGAWAI/WEBBERKAH)
# ======================================================================
@perizinan_ns.route("/pengajuan-izin")
class AjukanIzinResource(Resource):

    @jwt_required()
    @perizinan_ns.expect(izin_parser)
    @measure_execution_time
    def post(self):
        """(pegawai) Ajukan izin"""

        id_pegawai = int(get_jwt_identity())
        args = izin_parser.parse_args()

        id_jenis_izin = args["id_jenis_izin"]
        alasan = args["alasan"]
        file = args.get("lampiran")

        try:
            tgl_mulai = datetime.strptime(
                args["tanggal_mulai"], "%Y-%m-%d"
            ).date()
            tgl_selesai = datetime.strptime(
                args["tanggal_selesai"], "%Y-%m-%d"
            ).date()
        except ValueError:
            raise ValidationError("Format tanggal harus YYYY-MM-DD")

        if tgl_selesai < tgl_mulai:
            raise ValidationError("Tanggal selesai tidak boleh lebih kecil dari tanggal mulai")

        path_lampiran = None
        if file:
            path_lampiran = upload_lampiran_izin_to_cdn(file)

        id_izin = insert_pengajuan_izin(
            id_pegawai=id_pegawai,
            id_jenis_izin=id_jenis_izin,
            tgl_mulai=tgl_mulai,
            tgl_selesai=tgl_selesai,
            keterangan=alasan,
            path_lampiran=path_lampiran
        )

        return success(
            message="Pengajuan izin berhasil dikirim",
            data={
                "id_izin": id_izin,
                "status": "pending"
            }
        )

# ======================================================================
# ENDPOINT IZIN AKTIF OLEH PEGAWAI (PEGAWAI/WEBBERKAH)
# ======================================================================
@perizinan_ns.route("/aktif")
class IzinAktifHarianResource(Resource):

    @jwt_required()
    @perizinan_ns.expect(izin_aktif, validate=False)
    @measure_execution_time
    def get(self):
        """(pegawai) Ambil izin aktif harian"""

        id_pegawai = int(get_jwt_identity())
        args = izin_aktif.parse_args()

        tanggal_str = args.get("tanggal")
        if tanggal_str:
            try:
                tanggal = datetime.strptime(tanggal_str, "%Y-%m-%d").date()
            except ValueError:
                raise ValidationError("Format tanggal harus YYYY-MM-DD")
        else:
            tanggal = get_wita().date()

        izin_list = get_izin_aktif_harian(
            id_pegawai=id_pegawai,
            tanggal=tanggal
        )

        return success(
            message="Data izin aktif harian",
            data=[
                {
                    "id_izin": i["id_izin"],
                    "id_jenis_izin": i["id_jenis_izin"],
                    "nama_izin": i["nama_izin"],
                    "tgl_mulai": i["tgl_mulai"].isoformat(),
                    "tgl_selesai": i["tgl_selesai"].isoformat(),
                    "keterangan": i["keterangan"],
                    "lampiran": i["path_lampiran"],
                    "status_approval": i["status_approval"]
                }
                for i in izin_list
            ],
            meta={
                "tanggal": tanggal.isoformat(),
                "total": len(izin_list)
            }
        )

# ======================================================================
# ENDPOINT LIST IZIN PRIBADI OLEH PEGAWAI (PEGAWAI/WEBBERKAH)
# ======================================================================
@perizinan_ns.route("/history")
class IzinHistoryResource(Resource):

    @jwt_required()
    @perizinan_ns.expect(izin_history_parser)
    @measure_execution_time
    def get(self):
        """(pegawai) History izin bulanan"""

        id_pegawai = int(get_jwt_identity())
        args = izin_history_parser.parse_args()

        now = get_wita().date()

        bulan = args.get("bulan") or now.month
        tahun = args.get("tahun") or now.year

        if bulan < 1 or bulan > 12:
            raise ValidationError("Bulan harus di antara 1-12")

        # tentukan range tanggal bulan
        start_date = date(tahun, bulan, 1)
        if bulan == 12:
            end_date = date(tahun + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = date(tahun, bulan + 1, 1) - timedelta(days=1)

        izin_list = get_history_izin_bulanan(
            id_pegawai=id_pegawai,
            start_date=start_date,
            end_date=end_date
        )

        return success(
            message="History izin pegawai",
            data=[
                {
                    "id_izin": i["id_izin"],
                    "nama_izin": i["nama_izin"],
                    "tgl_mulai": i["tgl_mulai"].isoformat(),
                    "tgl_selesai": i["tgl_selesai"].isoformat(),
                    "keterangan": i["keterangan"],
                    "lampiran": i["path_lampiran"],
                    "status_approval": i["status_approval"],
                    "alasan_penolakan": i["alasan_penolakan"],
                    "created_at": i["created_at"].isoformat()
                }
                for i in izin_list
            ],
            meta={
                "bulan": bulan,
                "tahun": tahun,
                "total": len(izin_list)
            }
        )


# ======================================================================
# ENDPOINT DELETE IZIN OLEH ADMIN & PEGAWAI 
# ======================================================================
@perizinan_ns.route("/<int:id_izin>")
class IzinDeleteResource(Resource):

    @jwt_required()
    @measure_execution_time
    def delete(self, id_izin):
        """(pegawai/admin) Soft delete pengajuan izin"""

        id_pegawai = int(get_jwt_identity())
        jwt_data = get_jwt()
        account_type = jwt_data.get("account_type")

        izin = get_izin_by_id(id_izin)
        if not izin:
            raise ValidationError("Data izin tidak ditemukan")

        # validasi kepemilikan (jika pegawai)
        if account_type == "pegawai" and izin["id_pegawai"] != id_pegawai:
            raise ValidationError("Anda tidak berhak menghapus izin ini")

        # tidak boleh hapus izin yang sudah diproses
        if izin["status_approval"] in ("approved", "rejected"):
            raise ValidationError("Izin yang sudah diproses tidak dapat dihapus")

        soft_delete_izin(id_izin)

        return success(
            message="Pengajuan izin berhasil dihapus (soft delete)"
        )



# ======================================================================
# ENDPOINT LIST IZIN OLEH ADMIN (ADMIN/WEBBERKAH)
# ======================================================================
@perizinan_ns.route("")
class IzinListResource(Resource):

    @jwt_required()
    @role_required("admin")
    @perizinan_ns.expect(izin_list_parser)
    @measure_execution_time
    def get(self):
        """(admin) List data izin pegawai"""

        args = izin_list_parser.parse_args()

        now = get_wita()
        bulan = args.get("bulan") or now.month
        tahun = args.get("tahun") or now.year

        start_date = date(tahun, bulan, 1)
        last_day = monthrange(tahun, bulan)[1]
        end_date = date(tahun, bulan, last_day)

        # bulan berjalan → sampai hari ini
        if bulan == now.month and tahun == now.year:
            end_date = now.date()

        rows = get_izin_list(
            start_date=start_date,
            end_date=end_date,
            status_approval=args.get("status_approval"),
            id_departemen=args.get("id_departemen"),
            id_status_pegawai=args.get("id_status_pegawai"),
            id_pegawai=args.get("id_pegawai"),
            kategori_izin=args.get("kategori_izin")  # 🔹 IZIN / SAKIT / CUTI
        )

        return success(
            message="Data izin berhasil dimuat",
            data=[
                {
                    "id_izin": r["id_izin"],
                    "id_pegawai": r["id_pegawai"],
                    "nip": r["nip"],
                    "nama_panggilan": r["nama_panggilan"],
                    "nama_departemen": r["nama_departemen"],

                    "id_status_pegawai": r["id_status_pegawai"],
                    "status_pegawai": r["status_pegawai"],

                    "id_jenis_izin": r["id_jenis_izin"],
                    "kategori_izin": r["kategori_izin"],

                    "tgl_mulai": r["tgl_mulai"].isoformat() if r["tgl_mulai"] else None,
                    "tgl_selesai": r["tgl_selesai"].isoformat() if r["tgl_selesai"] else None,
                    "durasi_izin": r["durasi_izin"],

                    "status_approval": r["status_approval"],
                    "keterangan": r["keterangan"],
                    "path_lampiran": r["path_lampiran"],
                    "alasan_penolakan": r["alasan_penolakan"]
                }
                for r in rows
            ]
        )


# =========================================================================
# ENDPOINT PEGAWAI PUNYA IZIN UNTUK FILTER NAMA (ADMIN/WEBBERKAH)
# =========================================================================
@perizinan_ns.route("/pegawai")
class PegawaiDenganIzinResource(Resource):

    @jwt_required()
    @role_required("admin")
    @measure_execution_time
    def get(self):
        """(admin) List pegawai yang memiliki izin"""

        rows = get_pegawai_with_izin()

        return success(
            message="List pegawai dengan izin",
            data=[
                {
                    "id_pegawai": r["id_pegawai"],
                    "nip": r["nip"],
                    "nama_lengkap": r["nama_lengkap"],
                    "nama_panggilan": r["nama_panggilan"]
                }
                for r in rows
            ],
            meta={"total": len(rows)}
        )


# ======================================================================
# ENDPOINT APPROVE/REJECT IZIN OLEH ADMIN (ADMIN/WEBBERKAH)
# ======================================================================
@perizinan_ns.route("/<int:id_izin>/approved")
class IzinApproveResource(Resource):

    @jwt_required()
    @role_required("admin")
    @measure_execution_time
    def put(self, id_izin):
        """(admin) Approve perizinan"""
        izin = get_izin_by_id(id_izin)
        if not izin:
            raise ValidationError("Data perizinan tidak ditemukan")
        if izin["status_approval"] == "approved":
            raise ValidationError("Perizinan sudah di-approve")
        update_izin_approval(
            id_izin=id_izin,
            status_approval="approved",
            alasan_penolakan=None
        )
        return success(message="Perizinan berhasil di-approve")


@perizinan_ns.route("/<int:id_izin>/rejected")
class IzinRejectResource(Resource):

    @jwt_required()
    @role_required("admin")
    @perizinan_ns.expect(izin_reject_parser)
    @measure_execution_time
    def put(self, id_izin):
        """(admin) Reject perizinan"""
        args = izin_reject_parser.parse_args()
        alasan_penolakan = args.get("alasan_penolakan")
        izin = get_izin_by_id(id_izin)
        if not izin:
            raise ValidationError("Data perizinan tidak ditemukan")
        if izin["status_approval"] == "rejected":
            raise ValidationError("Perizinan sudah ditolak")
        update_izin_approval(
            id_izin=id_izin,
            status_approval="rejected",
            alasan_penolakan=alasan_penolakan
        )
        return success(message="Perizinan berhasil ditolak")
