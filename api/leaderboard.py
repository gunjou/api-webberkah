from calendar import monthrange
from flask_restx import Namespace, Resource, reqparse
from flask_jwt_extended import jwt_required
from datetime import date

from api.shared.response import success
from api.utils.decorator import measure_execution_time, role_required
from api.shared.helper import get_wita
from api.query.q_leaderboard import *


leaderboard_ns = Namespace("leaderboard", description="Manajemen Leaderboard Pegawai")

rekap_bulanan_parser = reqparse.RequestParser()
rekap_bulanan_parser.add_argument("bulan", type=int, required=False, help="Bulan (1-12)")
rekap_bulanan_parser.add_argument("tahun", type=int, required=False, help="Tahun (YYYY)")
rekap_bulanan_parser.add_argument("limit", type=int, required=False, help="Jumlah data yang ditampilkan")


@leaderboard_ns.route("/terlambat")
class LeaderboardTerlambatResource(Resource):

    @jwt_required()
    @role_required("admin")
    @leaderboard_ns.expect(rekap_bulanan_parser)
    @measure_execution_time
    def get(self):
        args = rekap_bulanan_parser.parse_args()

        now = get_wita()
        bulan = args.get("bulan") or now.month
        tahun = args.get("tahun") or now.year
        limit = args.get("limit") or 10

        start_date = date(tahun, bulan, 1)
        end_date = date(tahun, bulan, monthrange(tahun, bulan)[1])

        data = get_leaderboard_terlambat(start_date, end_date, limit)

        hasil = [
            {
                "id_pegawai": r["id_pegawai"],
                "nama": r["nama_lengkap"],
                "nama_panggilan": r["nama_panggilan"],
                "nip": r["nip"],
                "departemen": r["nama_departemen"],
                "status": r["nama_status"],
                "total_menit_terlambat": int(r["total_menit_terlambat"])
            }
            for r in data
        ]

        return success(
            data={
                "bulan": f"{tahun}-{str(bulan).zfill(2)}",
                "limit": limit,
                "data": hasil
            },
            message="Leaderboard keterlambatan pegawai"
        )