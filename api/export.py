from flask import request
from flask_restx import Namespace, Resource


from api.templates.pegawai_akun import render_pegawai_akun_pdf
from api.templates.pegawai_lokasi_absensi import render_pegawai_lokasi_absensi_pdf
from api.templates.pegawai_pendidikan import render_pegawai_pendidikan_pdf
from api.utils.decorator import measure_execution_time, role_required
from api.reports.r_pegawai import *

from api.templates.pegawai_report import render_pegawai_report_pdf
from api.templates.pegawai_rekening import render_pegawai_rekening_pdf


export_ns = Namespace("export", description="Manajemen Export Data Report")


# ==================================================
# ENDPOINTS REPORT UNTUK EXPORT PDF
# ==================================================
@export_ns.route("/report/pdf")
class PegawaiReportPdfResource(Resource):

    @role_required("admin")
    @measure_execution_time
    def get(self):
        """Akses: (admin), Export laporan pegawai PDF - Filter by status pegawai (optional)"""
        tab = request.args.get("tab")
        status = request.args.get("status")
        rows = get_pegawai_report_filtered(status_pegawai=status)

        suffix = status if status else "Semua"
        filename = f"Laporan Pegawai - {suffix}.pdf"

        return render_pegawai_report_pdf(
            pegawai_rows=rows,
            filename=filename
        )


@export_ns.route("/report/rekening/pdf")
class PegawaiRekeningPdfResource(Resource):

    @role_required("admin")
    @measure_execution_time
    def get(self):
        """Akses: (admin), Export list rekening pegawai PDF - Filter by status pegawai (optional)"""

        tab = request.args.get("tab")
        status = request.args.get("status")

        rows = get_pegawai_rekening_report_filtered(
            status_pegawai=status
        )

        suffix = status if status else "Semua"
        filename = f"List Rekening Pegawai - {suffix}.pdf"

        return render_pegawai_rekening_pdf(
            pegawai_rows=rows,
            filename=filename
        )


@export_ns.route("/report/pendidikan/pdf")
class PegawaiPendidikanPdfResource(Resource):

    @role_required("admin")
    @measure_execution_time
    def get(self):
        """Akses: (admin), Export data pendidikan pegawai PDF - Filter by status pegawai (optional)"""

        status = request.args.get("status")

        rows = get_pegawai_pendidikan_report_filtered(
            status_pegawai=status
        )

        suffix = status if status else "Semua"
        filename = f"Data Pendidikan Pegawai - {suffix}.pdf"

        return render_pegawai_pendidikan_pdf(
            pegawai_rows=rows,
            filename=filename
        )


@export_ns.route("/report/akun/pdf")
class PegawaiAkunPdfResource(Resource):

    # @role_required("admin")
    @measure_execution_time
    def get(self):
        """Akses: (admin), Export data akun pegawai PDF - Filter by status pegawai (optional)"""

        status = request.args.get("status")

        rows = get_pegawai_akun_report_filtered(
            status_pegawai=status
        )

        suffix = status if status else "Semua"
        filename = f"Data Akun Pegawai - {suffix}.pdf"

        return render_pegawai_akun_pdf(
            pegawai_rows=rows,
            filename=filename
        )


@export_ns.route("/report/lokasi-absensi/pdf")
class PegawaiLokasiAbsensiPdfResource(Resource):

    # @role_required("admin")
    @measure_execution_time
    def get(self):
        """
        Akses: (admin)
        Export data lokasi absensi pegawai PDF
        Filter by status pegawai (optional)
        """

        status = request.args.get("status")

        rows = get_pegawai_lokasi_absensi_report_filtered(
            status_pegawai=status
        )

        suffix = status if status else "Semua"
        filename = f"Data Lokasi Absensi Pegawai - {suffix}.pdf"

        return render_pegawai_lokasi_absensi_pdf(
            rows=rows,
            filename=filename
        )