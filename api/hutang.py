from datetime import datetime
from decimal import Decimal
from flask_restx import Namespace, Resource, reqparse
from flask_jwt_extended import get_jwt, jwt_required, get_jwt_identity

from api.shared.response import success
from api.shared.exceptions import ValidationError
from api.utils.decorator import measure_execution_time, role_required
from api.utils.uploader import upload_lampiran_izin_to_cdn
from api.query.q_hutang import *


hutang_ns = Namespace("hutang", description="Hutang Pegawai Endpoints")


# ======================================================================
# PARSER ENDPOINT HUTANG
# ======================================================================
hutang_summary_parser = reqparse.RequestParser()
hutang_summary_parser.add_argument("status_hutang", type=str, choices=("aktif", "lunas"), required=False, default="aktif", help="Filter status hutang (aktif | lunas)")

hutang_detail_parser = reqparse.RequestParser()
hutang_detail_parser.add_argument("status_hutang", type=str, choices=("aktif", "lunas"), default="aktif", location="args")
hutang_detail_parser.add_argument("jenis_transaksi", type=str, choices=("penambahan", "pembayaran"), location="args")

hutang_create_parser = reqparse.RequestParser()
hutang_create_parser.add_argument("id_pegawai", type=int, required=True, help="ID pegawai wajib diisi")
hutang_create_parser.add_argument("tanggal_pengajuan", type=str, required=True, help="Format YYYY-MM-DD")
hutang_create_parser.add_argument("jumlah_awal", type=float, required=True, help="Jumlah hutang awal")
hutang_create_parser.add_argument("keterangan", type=str, required=True, help="Keterangan hutang")
hutang_create_parser.add_argument("metode", type=str, choices=("kasbon", "kas", "transfer"), default="kasbon")

hutang_bayar_parser = reqparse.RequestParser()
hutang_bayar_parser.add_argument("id_pegawai", type=int, required=True, help="ID pegawai wajib diisi")
hutang_bayar_parser.add_argument("jumlah_bayar", type=float, required=True, help="Jumlah pembayaran hutang")
hutang_bayar_parser.add_argument("tanggal", type=str, required=True, help="Tanggal pembayaran (YYYY-MM-DD)")
hutang_bayar_parser.add_argument("metode", type=str, choices=("kas", "transfer", "potong_gaji"), default="potong_gaji")
hutang_bayar_parser.add_argument("keterangan", type=str, required=True, help="Keterangan pembayaran")

hutang_transaksi_bulanan_parser = reqparse.RequestParser()
hutang_transaksi_bulanan_parser.add_argument("bulan", type=int, required=True, help="Bulan (1-12)")
hutang_transaksi_bulanan_parser.add_argument("tahun", type=int, required=True, help="Tahun (YYYY)")


@hutang_ns.route("")
class HutangSummaryResource(Resource):
    
    @jwt_required()
    @role_required("admin")
    @hutang_ns.expect(hutang_create_parser)
    @measure_execution_time
    def post(self):
        """(admin) Tambah hutang pegawai"""

        args = hutang_create_parser.parse_args()

        # parsing tanggal
        try:
            tanggal_pengajuan = datetime.strptime(
                args["tanggal_pengajuan"],
                "%Y-%m-%d"
            ).date()
        except ValueError:
            raise ValidationError("Format tanggal_pengajuan harus YYYY-MM-DD")

        jumlah_awal = args["jumlah_awal"]
        if jumlah_awal <= 0:
            raise ValidationError("Jumlah hutang harus lebih dari 0")

        # insert hutang
        id_hutang = insert_hutang(
            id_pegawai=args["id_pegawai"],
            tanggal_pengajuan=tanggal_pengajuan,
            jumlah_awal=jumlah_awal,
            keterangan=args["keterangan"]
        )

        # insert transaksi penambahan
        insert_hutang_penambahan(
            id_hutang=id_hutang,
            jumlah=jumlah_awal,
            tanggal=tanggal_pengajuan,
            metode=args["metode"],
            keterangan="inisialisasi pinjaman"
        )

        return success(
            message="Hutang berhasil ditambahkan",
            data={
                "id_hutang": id_hutang,
                "status": "aktif",
                "jumlah_awal": jumlah_awal
            }
        )
        

    @jwt_required()
    @role_required("admin")
    @hutang_ns.expect(hutang_summary_parser, validate=False)
    @measure_execution_time
    def get(self):
        """(admin) Summary hutang pegawai"""

        args = hutang_summary_parser.parse_args()
        status_hutang = args.get("status_hutang", "aktif")

        hutang_rows = get_hutang_summary_base(status_hutang)

        hutang_ids = [h["id_hutang"] for h in hutang_rows]
        pembayaran_map = get_total_pembayaran_by_hutang(hutang_ids)

        pegawai_map = {}

        for h in hutang_rows:
            pid = h["id_pegawai"]

            if pid not in pegawai_map:
                pegawai_map[pid] = {
                    "id_pegawai": pid,
                    "nama": h["nama_lengkap"],
                    "nip": h["nip"],
                    "total_hutang": 0,
                    "total_pinjaman": 0,
                    "total_dibayar": 0,
                    "sisa_hutang": 0,
                    "last_update": None
                }

            p = pegawai_map[pid]

            p["total_hutang"] += 1
            p["total_pinjaman"] += h["jumlah_awal"]
            p["sisa_hutang"] += h["sisa_hutang"]
            p["total_dibayar"] += pembayaran_map.get(h["id_hutang"], 0)

            if not p["last_update"] or h["updated_at"] > p["last_update"]:
                p["last_update"] = h["updated_at"]

        return success(
            message="Summary hutang pegawai",
            data=[
                {
                    **p,
                    "total_pinjaman": float(p["total_pinjaman"]),
                    "total_dibayar": float(p["total_dibayar"]),
                    "sisa_hutang": float(p["sisa_hutang"]),
                    "last_update": p["last_update"].isoformat() if p["last_update"] else None,
                    "status": status_hutang
                }
                for p in pegawai_map.values()
            ],
            meta={
                "status_hutang": status_hutang,
                "total": len(pegawai_map)
            }
        )



@hutang_ns.route("/pegawai/<int:id_pegawai>")
class HutangPegawaiDetailResource(Resource):

    @jwt_required()
    @role_required("admin")
    @hutang_ns.expect(hutang_detail_parser, validate=False)
    @measure_execution_time
    def get(self, id_pegawai):
        """(admin) Detail hutang pegawai"""

        args = hutang_detail_parser.parse_args()
        status_hutang = args["status_hutang"]
        jenis_transaksi = args.get("jenis_transaksi")

        hutang_list = get_hutang_by_pegawai(
            id_pegawai=id_pegawai,
            status_hutang=status_hutang
        )

        hutang_ids = [h["id_hutang"] for h in hutang_list]
        transaksi_rows = get_transaksi_by_hutang_ids(
            hutang_ids,
            jenis_transaksi
        )

        # group transaksi by id_hutang
        transaksi_map = {}
        for t in transaksi_rows:
            transaksi_map.setdefault(t["id_hutang"], []).append(t)

        # summary
        total_pinjaman = sum(h["jumlah_awal"] for h in hutang_list)
        sisa_hutang = sum(h["sisa_hutang"] for h in hutang_list)
        total_dibayar = sum(
            t["jumlah"]
            for t in transaksi_rows
            if t["jenis_transaksi"] == "pembayaran"
        )

        return success(
            message="Detail hutang pegawai",
            data={
                "id_pegawai": id_pegawai,
                "nama_pegawai": hutang_list[0]["nama_lengkap"] if hutang_list else None,
                "status_hutang": status_hutang,
                "summary": {
                    "total_hutang": len(hutang_list),
                    "total_pinjaman": float(total_pinjaman),
                    "total_dibayar": float(total_dibayar),
                    "sisa_hutang": float(sisa_hutang)
                },
                "hutang": [
                    {
                        **h,
                        "transaksi": [
                            {
                                **t,
                                "tanggal": t["tanggal"].isoformat()
                            }
                            for t in transaksi_map.get(h["id_hutang"], [])
                        ]
                    }
                    for h in hutang_list
                ]
            }
        )



# hutang.py
@hutang_ns.route("/pembayaran")
class HutangPembayaranResource(Resource):

    @jwt_required()
    @role_required("admin")
    @hutang_ns.expect(hutang_bayar_parser)
    @measure_execution_time
    def post(self):
        """(admin) Pembayaran hutang pegawai (FIFO)"""

        args = hutang_bayar_parser.parse_args()

        try:
            tanggal = datetime.strptime(args["tanggal"], "%Y-%m-%d").date()
        except ValueError:
            raise ValidationError("Format tanggal harus YYYY-MM-DD")

        jumlah_bayar = Decimal(str(args["jumlah_bayar"]))
        if jumlah_bayar <= 0:
            raise ValidationError("Jumlah pembayaran harus lebih dari 0")

        hutang_list = get_hutang_aktif_pegawai(args["id_pegawai"])
        if not hutang_list:
            raise ValidationError("Pegawai tidak memiliki hutang aktif")

        sisa_bayar = jumlah_bayar
        total_terbayar = 0

        for h in hutang_list:
            if sisa_bayar <= 0:
                break

            saldo_awal = h["sisa_hutang"]

            if sisa_bayar >= saldo_awal:
                bayar = saldo_awal
                saldo_akhir = 0
            else:
                bayar = sisa_bayar
                saldo_akhir = saldo_awal - bayar

            insert_hutang_pembayaran(
                id_hutang=h["id_hutang"],
                jumlah=bayar,
                saldo_sebelum=saldo_awal,
                saldo_setelah=saldo_akhir,
                tanggal=tanggal,
                metode=args["metode"],
                keterangan=args["keterangan"]
            )

            update_hutang_sisa(
                id_hutang=h["id_hutang"],
                sisa_hutang=saldo_akhir
            )

            sisa_bayar -= bayar
            total_terbayar += bayar

        if sisa_bayar > 0:
            raise ValidationError(
                "Jumlah pembayaran melebihi total hutang aktif pegawai"
            )

        return success(
            message="Pembayaran hutang berhasil diproses",
            data={
                "id_pegawai": args["id_pegawai"],
                "total_dibayar": total_terbayar,
                "tanggal": tanggal.isoformat()
            }
        )
    
    
    @jwt_required()
    @role_required("admin")
    @hutang_ns.expect(hutang_transaksi_bulanan_parser)
    @measure_execution_time
    def get(self):
        """(admin) Ambil transaksi pembayaran hutang per bulan"""

        args = hutang_transaksi_bulanan_parser.parse_args()
        bulan = args["bulan"]
        tahun = args["tahun"]

        if bulan < 1 or bulan > 12:
            raise ValidationError("Bulan harus antara 1 - 12")

        rows = get_transaksi_pembayaran_hutang_bulanan(
            bulan=bulan,
            tahun=tahun
        )

        return success(
            message="Data transaksi pembayaran hutang",
            data=[
                {
                    "id_transaksi": r["id_transaksi"],
                    "id_hutang": r["id_hutang"],
                    "id_pegawai": r["id_pegawai"],
                    "nama_lengkap": r["nama_lengkap"],
                    "tanggal": r["tanggal"].isoformat(),
                    "jumlah": float(r["jumlah"]),
                    "metode": r["metode"],
                    "keterangan": r["keterangan"]
                }
                for r in rows
            ],
            meta={
                "bulan": bulan,
                "tahun": tahun,
                "total": len(rows)
            }
        )
