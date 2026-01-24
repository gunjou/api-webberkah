from calendar import monthrange
from flask_restx import Namespace, Resource, reqparse
from flask_jwt_extended import jwt_required
from datetime import date, datetime, time

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

rekap_bulanan_parser = reqparse.RequestParser()
rekap_bulanan_parser.add_argument("bulan", type=int, required=False, help="Bulan (1-12)")
rekap_bulanan_parser.add_argument("tahun", type=int, required=False, help="Tahun (YYYY)")
rekap_bulanan_parser.add_argument("id_departemen", type=int, required=False, help="Filter departemen")
rekap_bulanan_parser.add_argument("id_status_pegawai", type=int, required=False, help="Filter status pegawai")

detail_rekap_parser = reqparse.RequestParser()
detail_rekap_parser.add_argument("bulan", type=int, required=False, help="Bulan (1-12)")
detail_rekap_parser.add_argument("tahun", type=int, required=False, help="Tahun (YYYY)")


# ======================================================================
# HELPER FUNCTION
# ======================================================================
def parse_time(value):
    if not value:
        return None

    if isinstance(value, time):
        return value

    if isinstance(value, str):
        try:
            return datetime.strptime(value, "%H:%M").time()
        except ValueError:
            raise ValidationError("Format waktu harus HH:MM")

    raise ValidationError("Format waktu tidak valid")


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
            jam_mulai=parse_time(args.get("istirahat_mulai")),
            jam_selesai=parse_time(args.get("istirahat_selesai")),
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
        existing = get_absensi_existing(args["id_pegawai"], tanggal)
        if existing and existing["status"] == 1:
            raise ValidationError("Absensi pada tanggal ini sudah ada")

        # 3️⃣ Ambil jam kerja
        jam_kerja = get_jam_kerja_by_id(args["id_jam_kerja"])
        if not jam_kerja:
            raise ValidationError("Jam kerja tidak valid")

        menit_terlambat = hitung_menit_terlambat(
            jam_masuk,
            jam_kerja["jam_mulai"]
        )

        if existing and existing["status"] == 0:
            # 🔁 revive data lama
            id_absensi = existing["id_absensi"]
            deactivate_istirahat_by_absensi(id_absensi)

            revive_absensi_manual(
                id_absensi=id_absensi,
                id_jam_kerja=args["id_jam_kerja"],
                jam_masuk=jam_masuk,
                jam_keluar=jam_keluar,
                id_lokasi_masuk=args["id_lokasi_masuk"],
                id_lokasi_keluar=args.get("id_lokasi_keluar"),
                menit_terlambat=menit_terlambat
            )
        else:
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
                jam_mulai=parse_time(ist_mulai),
                jam_selesai=parse_time(ist_selesai),
                id_lokasi_balik=args.get("id_lokasi_istirahat")
            )

        # 6️⃣ Recalculate
        recalc_absensi(id_absensi)

        return success(
            message="Presensi manual berhasil ditambahkan",
            data={"id_absensi": id_absensi}
        )


# ======================================================================
# ENDPOINT LIHAT KEHADIRAN BULANAN SEMUA PEGAWAI (ADMIN/REKAPAN)
# ======================================================================
@presensi_ns.route("/rekap-bulanan")
class PresensiRekapBulananResource(Resource):

    @jwt_required()
    @role_required("admin")
    @presensi_ns.expect(rekap_bulanan_parser)
    @measure_execution_time
    def get(self):
        args = rekap_bulanan_parser.parse_args()

        now = get_wita()
        bulan = args.get("bulan") or now.month
        tahun = args.get("tahun") or now.year
        id_departemen = args.get("id_departemen")
        id_status_pegawai = args.get("id_status_pegawai")

        start_date = date(tahun, bulan, 1)
        last_day = monthrange(tahun, bulan)[1]
        end_date = date(tahun, bulan, last_day)

        is_bulan_berjalan = (bulan == now.month and tahun == now.year)
        today = now.date()

        pegawai_list = get_pegawai_rekap(
            id_departemen=id_departemen,
            id_status_pegawai=id_status_pegawai
        )

        absensi_map = get_absensi_map(start_date, end_date)
        izin_map = get_izin_map(start_date, end_date)
        hari_libur = get_hari_libur_map(start_date, end_date)

        hasil = []

        for p in pegawai_list:
            daily = {}
            hadir = izin = sakit = cuti = alpha = 0
            total_kurang_jam = 0

            current = start_date
            while current <= end_date:
                day = str(current.day)

                if is_bulan_berjalan and current > today:
                    daily[day] = None

                elif current.weekday() == 6 or current in hari_libur:
                    daily[day] = "L"

                elif current in izin_map.get(p["id_pegawai"], {}):
                    kategori = izin_map[p["id_pegawai"]][current]

                    if kategori == "IZIN":
                        daily[day] = "I"
                        izin += 1
                    elif kategori == "SAKIT":
                        daily[day] = "S"
                        sakit += 1
                    elif kategori == "CUTI":
                        daily[day] = "C"
                        cuti += 1

                elif current in absensi_map.get(p["id_pegawai"], {}):
                    daily[day] = "H"
                    hadir += 1

                    menit_telat = (
                        absensi_map[p["id_pegawai"]][current].get("menit_terlambat") or 0
                    )
                    total_kurang_jam += menit_telat

                else:
                    daily[day] = "A"
                    alpha += 1

                current += timedelta(days=1)

            hasil.append({
                "id_pegawai": p["id_pegawai"],
                "nama": p["nama_lengkap"],
                "nama_panggilan": p["nama_panggilan"],
                "nip": p["nip"],
                "id_departemen": p["id_departemen"],
                "nama_departemen": p["nama_departemen"],
                "id_status_pegawai": p["id_status_pegawai"],
                "nama_status": p["nama_status"],
                "hadir": hadir,
                "izin": izin,
                "sakit": sakit,
                "cuti": cuti,
                "alpha": alpha,
                "total_kurang_jam": total_kurang_jam,
                "daily": daily
            })

        return success(
            data={
                "bulan": f"{tahun}-{str(bulan).zfill(2)}",
                "total_hari": end_date.day,
                "data": hasil
            },
            message="Rekap presensi bulanan"
        )



# ======================================================================
# ENDPOINT DETAIL REKAPAN BULANAN PER PEGAWAI (ADMIN/REKAPAN)
# ======================================================================
@presensi_ns.route("/detail-rekap/<int:id_pegawai>")
class PresensiDetailRekapResource(Resource):

    @jwt_required()
    @role_required("admin")
    @presensi_ns.expect(detail_rekap_parser)
    @measure_execution_time
    def get(self, id_pegawai):
        args = detail_rekap_parser.parse_args()

        now = get_wita()
        bulan = args.get("bulan") or now.month
        tahun = args.get("tahun") or now.year

        start_date = date(tahun, bulan, 1)
        last_day = monthrange(tahun, bulan)[1]
        end_date = date(tahun, bulan, last_day)

        is_bulan_berjalan = (bulan == now.month and tahun == now.year)
        today = now.date()

        pegawai = get_pegawai_detail_rekap(id_pegawai)
        if not pegawai:
            raise ValidationError("Pegawai tidak ditemukan")

        absensi_map = get_absensi_detail_map(id_pegawai, start_date, end_date)
        izin_map = get_izin_map(start_date, end_date)
        hari_libur = get_hari_libur_map(start_date, end_date)

        logs = []
        current = start_date

        while current <= end_date:
            day = current.day
            row = absensi_map.get(current)

            if is_bulan_berjalan and current > today:
                logs.append({
                    "tanggal_hari": day,
                    "status": None,
                    "jam_masuk": None,
                    "jam_keluar": None,
                    "istirahat_mulai": None,
                    "istirahat_selesai": None,
                    "lokasi_masuk": None,
                    "lokasi_keluar": None,
                    "menit_terlambat": 0,
                    "menit_kurang_jam": 0
                })
                current += timedelta(days=1)
                continue

            if current.weekday() == 6 or current in hari_libur:
                status = "L"
            elif current in izin_map.get(id_pegawai, {}):
                kategori = izin_map[id_pegawai][current]
                if kategori == "IZIN":
                    status = "I"
                elif kategori == "SAKIT":
                    status = "S"
                elif kategori == "CUTI":
                    status = "C"
                else:
                    status = "A"
            elif row:
                status = "H"
            else:
                status = "A"

            logs.append({
                "tanggal_hari": day,
                "id_absensi": row["id_absensi"] if row else None,
                "status": status,

                "jam_masuk": row["jam_masuk"].strftime("%H:%M") if row and row["jam_masuk"] else None,
                "id_lokasi_masuk": row["id_lokasi_masuk"] if row else None,

                "jam_keluar": row["jam_keluar"].strftime("%H:%M") if row and row["jam_keluar"] else None,
                "id_lokasi_keluar": row["id_lokasi_keluar"] if row else None,

                "istirahat_mulai": (
                    row["jam_mulai_istirahat"].strftime("%H:%M")
                    if row and row["jam_mulai_istirahat"] else None
                ),
                "istirahat_selesai": (
                    row["jam_selesai_istirahat"].strftime("%H:%M")
                    if row and row["jam_selesai_istirahat"] else None
                ),
                "id_lokasi_istirahat": row["id_lokasi_istirahat"] if row else None,

                "menit_terlambat": row["menit_terlambat"] if row else 0,
                "menit_kurang_jam": (
                    max(0, (row["jam_per_hari"] - 60) - (row["total_menit_kerja"] or 0))
                    if row else 0
                ) # -60 karena jam kerja 480 aktuan 420 
            })


            current += timedelta(days=1)

        return success(
            message="Detail rekap harian pegawai",
            data={
                "id_pegawai": pegawai["id_pegawai"],
                "nama": pegawai["nama_lengkap"],
                "nip": pegawai["nip"],
                "nama_departemen": pegawai["nama_departemen"],
                "logs": logs
            }
        )
