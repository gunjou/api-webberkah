from flask_restx import Namespace, Resource, fields, reqparse
from flask import request
from flask_jwt_extended import jwt_required

from api.shared.response import success
from api.shared.exceptions import ValidationError
from api.utils.decorator import measure_execution_time, role_required
from api.query.q_payroll import *

payroll_ns = Namespace("payroll", description="Payroll")

simulate_model = payroll_ns.model("PayrollSimulate", {
    "id_pegawai": fields.Integer(required=True),
    "bulan": fields.Integer(required=True, min=1, max=12),
    "tahun": fields.Integer(required=True)
})

generate_model = payroll_ns.model("GeneratePayroll", {
    "bulan": fields.Integer(required=True, min=1, max=12),
    "tahun": fields.Integer(required=True)
})

payroll_list_parser = reqparse.RequestParser()
payroll_list_parser.add_argument("periode", type=str, required=True, help="Periode wajib diisi, format MM-YYYY (contoh: 01-2026)", location="args")

@payroll_ns.route("")
class PayrollListResource(Resource):

    @role_required("admin")
    @payroll_ns.expect(payroll_list_parser)
    @measure_execution_time
    def get(self):
        """
        Akses: admin
        Dashboard payroll per periode
        """
        args = payroll_list_parser.parse_args()
        periode = args.get("periode")

        try:
            bulan, tahun = periode.split("-")
            bulan = int(bulan)
            tahun = int(tahun)
        except ValueError:
            raise ValidationError("Format periode harus MM-YYYY, contoh: 01-2026")

        result = get_payroll_by_periode(bulan, tahun)

        return success(
            data=result,
            message="List payroll berhasil"
        )


@payroll_ns.route("/simulate")
class PayrollSimulateResource(Resource):

    @role_required("admin")
    @payroll_ns.expect(simulate_model, validate=True)
    @measure_execution_time
    def post(self):
        """
        Akses: (admin)
        Simulasi payroll pegawai (tanpa menyimpan data)
        """
        body = request.get_json(silent=True) or {}

        result = simulate_payroll(
            id_pegawai=body["id_pegawai"],
            bulan=body["bulan"],
            tahun=body["tahun"]
        )

        return success(data=result, message="Simulasi payroll berhasil")
    

@payroll_ns.route("/generate")
class PayrollGenerateResource(Resource):

    @role_required("admin")
    @payroll_ns.expect(generate_model, validate=True)
    @measure_execution_time
    def post(self):
        """
        Akses: admin
        Generate payroll seluruh pegawai (1 periode)
        """
        body = request.get_json(silent=True) or {}

        result = generate_payroll(
            bulan=body["bulan"],
            tahun=body["tahun"]
        )

        return success(
            data=result,
            message="Generate payroll berhasil"
        )



@payroll_ns.route("/komponen-gaji")
class PayrollKomponenGajiListResource(Resource):

    @role_required("admin")
    @measure_execution_time
    def get(self):
        """
        Akses: admin
        Ambil komponen gaji seluruh pegawai aktif
        """
        data = get_komponen_gaji_semua_pegawai()

        return success(
            data=data,
            message="Komponen gaji seluruh pegawai berhasil diambil"
        )
