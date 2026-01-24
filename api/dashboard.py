# api/dashboard.py
from flask_restx import Namespace, Resource
from flask_jwt_extended import jwt_required

from api.utils.decorator import role_required, measure_execution_time
from api.shared.response import success
from api.shared.helper import serialize_value
from api.query.q_dashboard import *


dashboard_ns = Namespace("dashboard", description="Dashboard Admin")


# ======================================================================
# ENDPOINT COUNT TOTAL NOTIFIKASI DI LONCENG NAVBAR (ADMIN/WEBBERKAH)
# ======================================================================
@dashboard_ns.route("/notifikasi/count")
class DashboardNotifikasiCountResource(Resource):

    @jwt_required()
    @role_required("admin")
    @measure_execution_time
    def get(self):
        """
        (admin) Count notifikasi izin & lembur pending
        """

        result = get_dashboard_notifikasi_count()

        izin_pending = result["izin_pending"] or 0
        lembur_pending = result["lembur_pending"] or 0

        return success(
            message="Jumlah notifikasi pending",
            data={
                "izin_pending": izin_pending,
                "lembur_pending": lembur_pending,
                "total": izin_pending + lembur_pending
            }
        )


# ======================================================================
# ENDPOINT COUNT TOTAL PEGAWAI AKTIF CARD DASHBOARD (ADMIN/WEBBERKAH)
# ======================================================================
@dashboard_ns.route("/pegawai-aktif/count")
class DashboardCountPegawaiAktifResource(Resource):

    @jwt_required()
    @role_required("admin")
    @measure_execution_time
    def get(self):
        """
        (admin) Hitung jumlah pegawai aktif
        """

        total = count_pegawai_aktif_dashboard()

        return success(
            message="Jumlah pegawai aktif",
            data={
                "total": total
            }
        )


# ======================================================================
# ENDPOINT LIST PEGAWAI AKTIF SECARA UMUM (ADMIN/WEBBERKAH)
# ======================================================================
@dashboard_ns.route("/pegawai-aktif")
class DashboardPegawaiAktifResource(Resource):

    @jwt_required()
    @role_required("admin")
    @measure_execution_time
    def get(self):
        """
        (admin) Data pegawai aktif untuk dashboard
        """

        result = get_pegawai_aktif_dashboard()

        return success(
            message="Data pegawai aktif",
            data=result,
            meta={"total": len(result)}
        )


# ======================================================================
# ENDPOINT LIST PEGAWAI HADIR HARI INI DI DASHBOARD (ADMIN/WEBBERKAH)
# ======================================================================
@dashboard_ns.route("/hadir-hari-ini")
class DashboardPresensiHariIniResource(Resource):

    @jwt_required()
    @role_required("admin")
    @measure_execution_time
    def get(self):
        """
        (admin) Data presensi pegawai yang hadir hari ini
        """

        result = get_presensi_hadir_hari_ini_simple()

        return success(
            message="Data presensi hadir hari ini",
            data=result,
            meta={"total": len(result)}
        )


# ======================================================================
# ENDPOINT LIST PEGAWAI TERLAMBAT HARI INI DI DASHBOARD (ADMIN/WEBBERKAH)
# ======================================================================
@dashboard_ns.route("/terlambat-hari-ini")
class DashboardPresensiTerlambatHariIniResource(Resource):

    @jwt_required()
    @role_required("admin")
    @measure_execution_time
    def get(self):
        """
        (admin) Data presensi pegawai yang terlambat hari ini
        """

        result = get_presensi_terlambat_hari_ini_simple()

        return success(
            message="Data presensi pegawai terlambat hari ini",
            data={
                "items": result
            },
            meta={
                "total": len(result)
            }
        )


# ======================================================================
# ENDPOINT LIST PEGAWAI IZIN HARI INI DI DASHBOARD (ADMIN/WEBBERKAH)
# ======================================================================
@dashboard_ns.route("/izin-hari-ini")
class DashboardPegawaiIzinHariIniResource(Resource):

    @jwt_required()
    @role_required("admin")
    @measure_execution_time
    def get(self):
        """
        (admin) Data pegawai izin / sakit / cuti hari ini
        """

        result = get_pegawai_izin_hari_ini_dashboard()

        # ringkasan per kategori (opsional tapi recommended)
        summary = {
            "SAKIT": 0,
            "IZIN": 0,
            "CUTI": 0
        }

        for item in result:
            kategori = item.get("kategori_izin")
            if kategori in summary:
                summary[kategori] += 1

        return success(
            message="Data pegawai izin hari ini",
            data={
                "items": result
            },
            meta={
                "total": len(result),
                "summary": summary
            }
        )


# ======================================================================
# ENDPOINT LIST PEGAWAI ALPHA HARI INI DI DASHBOARD (ADMIN/WEBBERKAH)
# ======================================================================
@dashboard_ns.route("/alpha-hari-ini")
class DashboardPegawaiAlphaHariIniResource(Resource):

    @jwt_required()
    @role_required("admin")
    @measure_execution_time
    def get(self):
        """
        (admin) Data pegawai alpha hari ini
        """

        result = get_pegawai_alpha_hari_ini()

        return success(
            message="Data pegawai alpha hari ini",
            data={
                "items": result
            },
            meta={
                "total": len(result)
            }
        )


# ======================================================================
# ENDPOINT LIST SEBARAN LOKASI ABSENSI DI DASHBOARD (ADMIN/WEBBERKAH)
# ======================================================================
@dashboard_ns.route("/sebaran-lokasi-hari-ini")
class DashboardSebaranLokasiHariIniResource(Resource):

    @jwt_required()
    @role_required("admin")
    @measure_execution_time
    def get(self):
        """
        (admin) Sebaran pegawai hadir hari ini per lokasi absensi
        """

        result = get_sebaran_presensi_lokasi_hari_ini()

        return success(
            message="Sebaran presensi pegawai per lokasi hari ini",
            data={
                "items": result
            },
            meta={
                "total_lokasi": len(result),
                "total_pegawai": sum(item["total"] for item in result)
            }
        )