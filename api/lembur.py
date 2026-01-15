from flask_restx import Namespace, Resource, reqparse
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.datastructures import FileStorage
from datetime import datetime, date, time

from api.shared.response import success
from api.shared.exceptions import ValidationError
from api.utils.decorator import measure_execution_time
from api.query.q_lembur import *
from api.utils.uploader import upload_lampiran_izin_to_cdn

lembur_ns = Namespace("lembur", description="Pengajuan Lembur Pegawai")



lembur_parser = reqparse.RequestParser()
lembur_parser.add_argument("id_jenis_lembur", type=int, required=True, location="form", help="Jenis lembur wajib diisi")
lembur_parser.add_argument("tanggal", type=str, required=True, location="form", help="Tanggal lembur (YYYY-MM-DD)")
lembur_parser.add_argument("jam_mulai", type=str, required=True, location="form", help="Jam mulai lembur (HH:MM)")
lembur_parser.add_argument("jam_selesai", type=str, required=True, location="form", help="Jam selesai lembur (HH:MM)")
lembur_parser.add_argument("keterangan", type=str, required=False, location="form")
lembur_parser.add_argument("lampiran", type=FileStorage, location="files", required=False)

lembur_harian_parser = reqparse.RequestParser()
lembur_harian_parser.add_argument("tanggal", type=str, required=False, location="args", help="Tanggal lembur (YYYY-MM-DD), default hari ini")

lembur_history_parser = reqparse.RequestParser()
lembur_history_parser.add_argument("bulan", type=int, required=False, location="args", help="Bulan (1-12), default bulan ini")
lembur_history_parser.add_argument("tahun", type=int, required=False, location="args", help="Tahun (YYYY), default tahun ini")


@lembur_ns.route("/pengajuan-lembur")
class PengajuanLemburResource(Resource):

    @jwt_required()
    @lembur_ns.expect(lembur_parser)
    @measure_execution_time
    def post(self):
        """(pegawai) Pengajuan lembur"""

        id_pegawai = int(get_jwt_identity())
        args = lembur_parser.parse_args()

        try:
            tanggal = datetime.strptime(args["tanggal"], "%Y-%m-%d").date()
            jam_mulai = datetime.strptime(args["jam_mulai"], "%H:%M").time()
            jam_selesai = datetime.strptime(args["jam_selesai"], "%H:%M").time()
        except ValueError:
            raise ValidationError("Format tanggal / jam tidak valid")

        if jam_selesai <= jam_mulai:
            raise ValidationError("Jam selesai harus lebih besar dari jam mulai")

        menit_lembur = int(
            (datetime.combine(tanggal, jam_selesai) -
             datetime.combine(tanggal, jam_mulai)
            ).total_seconds() / 60
        )

        # Upload lampiran ke CDN
        lampiran_url = upload_lampiran_izin_to_cdn(args.get("lampiran"))

        id_lembur = insert_pengajuan_lembur(
            id_pegawai=id_pegawai,
            id_jenis_lembur=args["id_jenis_lembur"],
            tanggal=tanggal,
            jam_mulai=jam_mulai,
            jam_selesai=jam_selesai,
            menit_lembur=menit_lembur,
            keterangan=args.get("keterangan"),
            path_lampiran=lampiran_url
        )

        return success(
            message="Pengajuan lembur berhasil",
            data={
                "id_lembur": id_lembur,
                "menit_lembur": menit_lembur,
                "lampiran": lampiran_url,
                "status_approval": "pending"
            }
        )


@lembur_ns.route("/aktif")
class LemburAktifHarianResource(Resource):

    @jwt_required()
    @lembur_ns.expect(lembur_harian_parser)
    @measure_execution_time
    def get(self):
        """(pegawai) Ambil lembur aktif hari ini"""

        id_pegawai = int(get_jwt_identity())
        args = lembur_harian_parser.parse_args()

        tanggal_str = args.get("tanggal")
        if tanggal_str:
            try:
                tanggal = datetime.strptime(
                    tanggal_str, "%Y-%m-%d"
                ).date()
            except ValueError:
                raise ValidationError("Format tanggal harus YYYY-MM-DD")
        else:
            tanggal = get_wita().date()

        lembur_list = get_lembur_aktif_harian(
            id_pegawai=id_pegawai,
            tanggal=tanggal
        )

        return success(
            message="Data lembur aktif harian",
            data=[
                {
                    "id_lembur": l["id_lembur"],
                    "id_jenis_lembur": l["id_jenis_lembur"],
                    "nama_jenis_lembur": l["nama_jenis"],
                    "tanggal": l["tanggal"].isoformat(),
                    "jam_mulai": l["jam_mulai"].strftime("%H:%M"),
                    "jam_selesai": l["jam_selesai"].strftime("%H:%M"),
                    "menit_lembur": l["menit_lembur"],
                    "status_approval": l["status_approval"],
                    "keterangan": l["keterangan"]
                }
                for l in lembur_list
            ],
            meta={
                "tanggal": tanggal.isoformat(),
                "total": len(lembur_list)
            }
        )


@lembur_ns.route("/history")
class LemburHistoryBulananResource(Resource):

    @jwt_required()
    @lembur_ns.expect(lembur_history_parser)
    @measure_execution_time
    def get(self):
        """(pegawai) History lembur bulanan"""

        id_pegawai = int(get_jwt_identity())
        args = lembur_history_parser.parse_args()

        now = get_wita()
        bulan = args.get("bulan") or now.month
        tahun = args.get("tahun") or now.year

        lembur_list = get_history_lembur_bulanan(
            id_pegawai=id_pegawai,
            bulan=bulan,
            tahun=tahun
        )

        return success(
            message="History lembur bulanan",
            data=[
                {
                    "id_lembur": l["id_lembur"],
                    "id_jenis_lembur": l["id_jenis_lembur"],
                    "nama_jenis_lembur": l["nama_jenis"],
                    "tanggal": l["tanggal"].isoformat(),
                    "jam_mulai": l["jam_mulai"].strftime("%H:%M"),
                    "jam_selesai": l["jam_selesai"].strftime("%H:%M"),
                    "menit_lembur": l["menit_lembur"],
                    "total_bayaran": l["total_bayaran"],
                    "status_approval": l["status_approval"],
                    "keterangan": l["keterangan"],
                    "alasan_penolakan": l["alasan_penolakan"]
                }
                for l in lembur_list
            ],
            meta={
                "bulan": bulan,
                "tahun": tahun,
                "total": len(lembur_list)
            }
        )