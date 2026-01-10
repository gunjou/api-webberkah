from flask_jwt_extended import jwt_required
from flask_restx import Namespace, Resource, fields
from flask import request
from datetime import datetime

from api.shared.response import success
from api.shared.exceptions import ValidationError, NotFoundError
from api.utils.decorator import measure_execution_time, role_required
from api.query.q_master import *


master_ns = Namespace("master", description="Master Data")

status_pegawai_model = master_ns.model("StatusPegawai", {
        "nama_status": fields.String(required=True, description="Nama status pegawai", example="Pegawai Tetap")
    }
)

departemen_model = master_ns.model("Departemen", {
        "nama_departemen": fields.String(required=True, description="Nama departemen", example="Human Resource")
    }
)

jabatan_model = master_ns.model("Jabatan", {
        "nama_jabatan": fields.String(required=True, description="Nama jabatan", example="Staff IT")
    }
)

level_jabatan_model = master_ns.model("LevelJabatan", {
        "nama_level": fields.String(required=True, description="Nama level jabatan", example="Senior"),
        "urutan_level": fields.Integer(required=True, description="Urutan level jabatan", example=1)
    }
)

jam_kerja_model = master_ns.model("JamKerja", {
        "nama_shift": fields.String(required=True, description="Nama shift kerja", example="Shift Pagi"),
        "jam_per_hari": fields.Integer(required=True, description="Durasi kerja per hari (menit)", example=480)
    }
)

lokasi_absensi_model = master_ns.model("LokasiAbsensi", {
        "nama_lokasi": fields.String(required=True, description="Nama lokasi absensi", example="Kantor Pusat"),
        "latitude": fields.Float(required=True, description="Latitude lokasi", example=-8.583069),
        "longitude": fields.Float(required=True, description="Longitude lokasi", example=116.320251),
        "radius_meter": fields.Integer(required=True, description="Radius absensi (meter)", example=100)
    }
)

jenis_izin_model = master_ns.model("JenisIzin", {
        "nama_izin": fields.String(required=True, description="Nama jenis izin", example="Izin Sakit"),
        "potong_cuti": fields.Boolean(required=True, description="Apakah izin memotong jatah cuti", example=False)
    }
)

jenis_lembur_model = master_ns.model("JenisLembur", {
        "nama_jenis": fields.String(required=True, description="Nama jenis lembur", example="Lembur Hari Kerja"),
        "deskripsi": fields.String(required=False, description="Deskripsi jenis lembur", example="Lembur di kantor")
    }
)

lembur_rule_model = master_ns.model("LemburRule", {
        "id_jenis_lembur": fields.Integer(required=True, description="ID jenis lembur", example=1),
        "urutan_jam": fields.Integer(required=True, description="Urutan jam lembur", example=1),
        "menit_dari": fields.Integer(required=True, description="Menit mulai lembur", example=0),
        "menit_sampai": fields.Integer(required=True, description="Menit akhir lembur", example=60),
        "pengali": fields.Float(required=True, description="Pengali perhitungan lembur", example=1.5)
    }
)

hari_libur_model = master_ns.model("HariLibur", {
        "tanggal": fields.String(required=True, description="Tanggal hari libur (YYYY-MM-DD)", example="2026-01-01"),
        "nama_libur": fields.String(required=True, description="Nama hari libur", example="Tahun Baru"),
        "jenis": fields.String(required=True, description="Jenis hari libur (nasional / internal)", example="nasional")
    }
)



# ==================================================
# REF STATUS PEGAWAI
# ==================================================
@master_ns.route("/status-pegawai")
class StatusPegawaiListResource(Resource):

    @jwt_required()
    @measure_execution_time
    def get(self):
        """Akses: (admin, pegawai), Get list status pegawai"""
        data = get_status_pegawai_list()
        return success(data=data, message="List status pegawai")

    @role_required('admin')
    @master_ns.expect(status_pegawai_model, validate=True)
    @measure_execution_time
    def post(self):
        """Akses: (admin), Add status pegawai baru"""
        body = request.get_json(silent=True) or {}
        nama_status = body.get("nama_status")

        if not nama_status:
            raise ValidationError("Nama status wajib diisi")

        data = create_status_pegawai(nama_status)
        return success(data=data, message="Status pegawai berhasil ditambahkan")


@master_ns.route("/status-pegawai/<int:id_status_pegawai>")
class StatusPegawaiDetailResource(Resource):

    @jwt_required()
    @measure_execution_time
    def get(self, id_status_pegawai):
        """Akses: (admin, pegawai), Get status pegawai by id"""
        data = get_status_pegawai_by_id(id_status_pegawai)
        if not data:
            raise NotFoundError("Status pegawai tidak ditemukan")

        return success(data=data, message="Detail status pegawai")

    @role_required('admin')
    @master_ns.expect(status_pegawai_model, validate=True)
    @measure_execution_time
    def put(self, id_status_pegawai):
        """Akses: (admin), Edit status pegawai by id"""
        body = request.get_json(silent=True) or {}
        nama_status = body.get("nama_status")

        if not nama_status:
            raise ValidationError("Nama status wajib diisi")

        data = update_status_pegawai(id_status_pegawai, nama_status)
        if not data:
            raise NotFoundError("Status pegawai tidak ditemukan")

        return success(data=data, message="Status pegawai berhasil diperbarui")

    @role_required('admin')
    @measure_execution_time
    def delete(self, id_status_pegawai):
        """Akses: (admin), Delete status pegawai by id"""
        deleted = delete_status_pegawai(id_status_pegawai)
        if deleted == 0:
            raise NotFoundError("Status pegawai tidak ditemukan")

        return success(message="Status pegawai berhasil dihapus")



# ==================================================
# REF DEPARTEMEN
# ==================================================
@master_ns.route("/departemen")
class DepartemenListResource(Resource):

    @jwt_required()
    @measure_execution_time
    def get(self):
        """Akses: (admin, pegawai), Get list departemen"""
        data = get_departemen_list()
        return success(data=data, message="List departemen")

    @role_required("admin")
    @master_ns.expect(departemen_model, validate=True)
    @measure_execution_time
    def post(self):
        """Akses: (admin), Add departemen baru"""
        body = request.get_json(silent=True) or {}
        nama_departemen = body.get("nama_departemen")

        if not nama_departemen:
            raise ValidationError("Nama departemen wajib diisi")

        data = create_departemen(nama_departemen)
        return success(data=data, message="Departemen berhasil ditambahkan")


@master_ns.route("/departemen/<int:id_departemen>")
class DepartemenDetailResource(Resource):

    @jwt_required()
    @measure_execution_time
    def get(self, id_departemen):
        """Akses: (admin, pegawai), Get departemen by id"""
        data = get_departemen_by_id(id_departemen)
        if not data:
            raise NotFoundError("Departemen tidak ditemukan")

        return success(data=data, message="Detail departemen")

    @role_required("admin")
    @master_ns.expect(departemen_model, validate=True)
    @measure_execution_time
    def put(self, id_departemen):
        """Akses: (admin), Edit departemen by id"""
        body = request.get_json(silent=True) or {}
        nama_departemen = body.get("nama_departemen")

        if not nama_departemen:
            raise ValidationError("Nama departemen wajib diisi")

        data = update_departemen(id_departemen, nama_departemen)
        if not data:
            raise NotFoundError("Departemen tidak ditemukan")

        return success(data=data, message="Departemen berhasil diperbarui")

    @role_required("admin")
    @measure_execution_time
    def delete(self, id_departemen):
        """Akses: (admin), Delete departemen by id"""
        deleted = delete_departemen(id_departemen)
        if deleted == 0:
            raise NotFoundError("Departemen tidak ditemukan")

        return success(message="Departemen berhasil dihapus")



# ==================================================
# REF JABATAN
# ==================================================
@master_ns.route("/jabatan")
class JabatanListResource(Resource):

    @jwt_required()
    @measure_execution_time
    def get(self):
        """Akses: (admin, pegawai), Get list jabatan"""
        data = get_jabatan_list()
        return success(data=data, message="List jabatan")

    @role_required("admin")
    @master_ns.expect(jabatan_model, validate=True)
    @measure_execution_time
    def post(self):
        """Akses: (admin), Add jabatan baru"""
        body = request.get_json(silent=True) or {}
        nama_jabatan = body.get("nama_jabatan")

        if not nama_jabatan:
            raise ValidationError("Nama jabatan wajib diisi")

        data = create_jabatan(nama_jabatan)
        return success(data=data, message="Jabatan berhasil ditambahkan")


@master_ns.route("/jabatan/<int:id_jabatan>")
class JabatanDetailResource(Resource):

    @jwt_required()
    @measure_execution_time
    def get(self, id_jabatan):
        """Akses: (admin, pegawai), Get jabatan by id"""
        data = get_jabatan_by_id(id_jabatan)
        if not data:
            raise NotFoundError("Jabatan tidak ditemukan")

        return success(data=data, message="Detail jabatan")

    @role_required("admin")
    @master_ns.expect(jabatan_model, validate=True)
    @measure_execution_time
    def put(self, id_jabatan):
        """Akses: (admin), Edit jabatan by id"""
        body = request.get_json(silent=True) or {}
        nama_jabatan = body.get("nama_jabatan")

        if not nama_jabatan:
            raise ValidationError("Nama jabatan wajib diisi")

        data = update_jabatan(id_jabatan, nama_jabatan)
        if not data:
            raise NotFoundError("Jabatan tidak ditemukan")

        return success(data=data, message="Jabatan berhasil diperbarui")

    @role_required("admin")
    @measure_execution_time
    def delete(self, id_jabatan):
        """Akses: (admin), Delete jabatan by id"""
        deleted = delete_jabatan(id_jabatan)
        if deleted == 0:
            raise NotFoundError("Jabatan tidak ditemukan")

        return success(message="Jabatan berhasil dihapus")



# ==================================================
# REF LEVEL JABATAN
# ==================================================
@master_ns.route("/level-jabatan")
class LevelJabatanListResource(Resource):

    @jwt_required()
    @measure_execution_time
    def get(self):
        """Akses: (admin, pegawai), Get list level jabatan"""
        data = get_level_jabatan_list()
        return success(data=data, message="List level jabatan")

    @role_required("admin")
    @master_ns.expect(level_jabatan_model, validate=True)
    @measure_execution_time
    def post(self):
        """Akses: (admin), Add level jabatan baru"""
        body = request.get_json(silent=True) or {}
        nama_level = body.get("nama_level")
        urutan_level = body.get("urutan_level")

        if not nama_level or urutan_level is None:
            raise ValidationError("Nama level dan urutan level wajib diisi")

        data = create_level_jabatan(nama_level, urutan_level)
        return success(data=data, message="Level jabatan berhasil ditambahkan")


@master_ns.route("/level-jabatan/<int:id_level_jabatan>")
class LevelJabatanDetailResource(Resource):

    @jwt_required()
    @measure_execution_time
    def get(self, id_level_jabatan):
        """Akses: (admin, pegawai), Get level jabatan by id"""
        data = get_level_jabatan_by_id(id_level_jabatan)
        if not data:
            raise NotFoundError("Level jabatan tidak ditemukan")

        return success(data=data, message="Detail level jabatan")

    @role_required("admin")
    @master_ns.expect(level_jabatan_model, validate=True)
    @measure_execution_time
    def put(self, id_level_jabatan):
        """Akses: (admin), Edit level jabatan by id"""
        body = request.get_json(silent=True) or {}
        nama_level = body.get("nama_level")
        urutan_level = body.get("urutan_level")

        if not nama_level or urutan_level is None:
            raise ValidationError("Nama level dan urutan level wajib diisi")

        data = update_level_jabatan(id_level_jabatan, nama_level, urutan_level)
        if not data:
            raise NotFoundError("Level jabatan tidak ditemukan")

        return success(data=data, message="Level jabatan berhasil diperbarui")

    @role_required("admin")
    @measure_execution_time
    def delete(self, id_level_jabatan):
        """Akses: (admin), Delete leveljabatan by id"""
        deleted = delete_level_jabatan(id_level_jabatan)
        if deleted == 0:
            raise NotFoundError("Level jabatan tidak ditemukan")

        return success(message="Level jabatan berhasil dihapus")



# ==================================================
# REF JAM KERJA
# ==================================================
@master_ns.route("/jam-kerja")
class JamKerjaListResource(Resource):

    @jwt_required()
    @measure_execution_time
    def get(self):
        """Akses: (admin, pegawai), Get list jam kerja"""
        data = get_jam_kerja_list()
        return success(data=data, message="List jam kerja")

    @role_required("admin")
    @master_ns.expect(jam_kerja_model, validate=True)
    @measure_execution_time
    def post(self):
        """Akses: (admin), Add jam kerja baru"""
        body = request.get_json(silent=True) or {}
        nama_shift = body.get("nama_shift")
        jam_per_hari = body.get("jam_per_hari")

        if not nama_shift or jam_per_hari is None:
            raise ValidationError("Nama shift dan jam kerja per hari wajib diisi")

        data = create_jam_kerja(nama_shift, jam_per_hari)
        return success(data=data, message="Jam kerja berhasil ditambahkan")


@master_ns.route("/jam-kerja/<int:id_jam_kerja>")
class JamKerjaDetailResource(Resource):

    @jwt_required()
    @measure_execution_time
    def get(self, id_jam_kerja):
        """Akses: (admin, pegawai), Get jam kerja by id"""
        data = get_jam_kerja_by_id(id_jam_kerja)
        if not data:
            raise NotFoundError("Jam kerja tidak ditemukan")

        return success(data=data, message="Detail jam kerja")

    @role_required("admin")
    @master_ns.expect(jam_kerja_model, validate=True)
    @measure_execution_time
    def put(self, id_jam_kerja):
        """Akses: (admin), Edit jam kerja by id"""
        body = request.get_json(silent=True) or {}
        nama_shift = body.get("nama_shift")
        jam_per_hari = body.get("jam_per_hari")

        if not nama_shift or jam_per_hari is None:
            raise ValidationError("Nama shift dan jam kerja per hari wajib diisi")

        data = update_jam_kerja(id_jam_kerja, nama_shift, jam_per_hari)
        if not data:
            raise NotFoundError("Jam kerja tidak ditemukan")

        return success(data=data, message="Jam kerja berhasil diperbarui")

    @role_required("admin")
    @measure_execution_time
    def delete(self, id_jam_kerja):
        """Akses: (admin), Delete jam kerja by id"""
        deleted = delete_jam_kerja(id_jam_kerja)
        if deleted == 0:
            raise NotFoundError("Jam kerja tidak ditemukan")

        return success(message="Jam kerja berhasil dihapus")



# ==================================================
# REF LOKASI ABSENSI
# ==================================================
@master_ns.route("/lokasi-absensi")
class LokasiAbsensiListResource(Resource):

    @jwt_required()
    @measure_execution_time
    def get(self):
        """Akses: (admin, pegawai), Get list lokasi absensi"""
        data = get_lokasi_absensi_list()
        return success(data=data, message="List lokasi absensi")

    @role_required("admin")
    @master_ns.expect(lokasi_absensi_model, validate=True)
    @measure_execution_time
    def post(self):
        """Akses: (admin), Add lokasi absensi baru"""
        body = request.get_json(silent=True) or {}

        nama_lokasi = body.get("nama_lokasi")
        latitude = body.get("latitude")
        longitude = body.get("longitude")
        radius_meter = body.get("radius_meter")

        if (
            not nama_lokasi
            or latitude is None
            or longitude is None
            or radius_meter is None
        ):
            raise ValidationError(
                "Nama lokasi, latitude, longitude, dan radius wajib diisi"
            )

        data = create_lokasi_absensi(
            nama_lokasi, latitude, longitude, radius_meter
        )
        return success(data=data, message="Lokasi absensi berhasil ditambahkan")


@master_ns.route("/lokasi-absensi/<int:id_lokasi>")
class LokasiAbsensiDetailResource(Resource):

    @jwt_required()
    @measure_execution_time
    def get(self, id_lokasi):
        """Akses: (admin, pegawai), Get lokasi absensi by id"""
        data = get_lokasi_absensi_by_id(id_lokasi)
        if not data:
            raise NotFoundError("Lokasi absensi tidak ditemukan")

        return success(data=data, message="Detail lokasi absensi")

    @role_required("admin")
    @master_ns.expect(lokasi_absensi_model, validate=True)
    @measure_execution_time
    def put(self, id_lokasi):
        """Akses: (admin), Edit lokasi absensi by id"""
        body = request.get_json(silent=True) or {}

        nama_lokasi = body.get("nama_lokasi")
        latitude = body.get("latitude")
        longitude = body.get("longitude")
        radius_meter = body.get("radius_meter")

        if (
            not nama_lokasi
            or latitude is None
            or longitude is None
            or radius_meter is None
        ):
            raise ValidationError(
                "Nama lokasi, latitude, longitude, dan radius wajib diisi"
            )

        data = update_lokasi_absensi(
            id_lokasi, nama_lokasi, latitude, longitude, radius_meter
        )
        if not data:
            raise NotFoundError("Lokasi absensi tidak ditemukan")

        return success(data=data, message="Lokasi absensi berhasil diperbarui")

    @role_required("admin")
    @measure_execution_time
    def delete(self, id_lokasi):
        """Akses: (admin), Delete lokasi absensi by id"""
        deleted = delete_lokasi_absensi(id_lokasi)
        if deleted == 0:
            raise NotFoundError("Lokasi absensi tidak ditemukan")

        return success(message="Lokasi absensi berhasil dihapus")



# ==================================================
# REF JENIS IZIN
# ==================================================
@master_ns.route("/jenis-izin")
class JenisIzinListResource(Resource):

    @jwt_required()
    @measure_execution_time
    def get(self):
        """Akses: (admin, pegawai), Get list jenis izin"""
        data = get_jenis_izin_list()
        return success(data=data, message="List jenis izin")

    @role_required("admin")
    @master_ns.expect(jenis_izin_model, validate=True)
    @measure_execution_time
    def post(self):
        """Akses: (admin), Add jenis izin baru"""
        body = request.get_json(silent=True) or {}

        nama_izin = body.get("nama_izin")
        potong_cuti = body.get("potong_cuti")

        if not nama_izin or potong_cuti is None:
            raise ValidationError(
                "Nama izin dan potong cuti wajib diisi"
            )

        data = create_jenis_izin(nama_izin, potong_cuti)
        return success(data=data, message="Jenis izin berhasil ditambahkan")


@master_ns.route("/jenis-izin/<int:id_jenis_izin>")
class JenisIzinDetailResource(Resource):

    @jwt_required()
    @measure_execution_time
    def get(self, id_jenis_izin):
        """Akses: (admin, pegawai), Get jenis izin by id"""
        data = get_jenis_izin_by_id(id_jenis_izin)
        if not data:
            raise NotFoundError("Jenis izin tidak ditemukan")

        return success(data=data, message="Detail jenis izin")

    @role_required("admin")
    @master_ns.expect(jenis_izin_model, validate=True)
    @measure_execution_time
    def put(self, id_jenis_izin):
        """Akses: (admin), Edit jenis izin by id"""
        body = request.get_json(silent=True) or {}

        nama_izin = body.get("nama_izin")
        potong_cuti = body.get("potong_cuti")

        if not nama_izin or potong_cuti is None:
            raise ValidationError(
                "Nama izin dan potong cuti wajib diisi"
            )

        data = update_jenis_izin(id_jenis_izin, nama_izin, potong_cuti)
        if not data:
            raise NotFoundError("Jenis izin tidak ditemukan")

        return success(data=data, message="Jenis izin berhasil diperbarui")

    @role_required("admin")
    @measure_execution_time
    def delete(self, id_jenis_izin):
        """Akses: (admin), Delete jenis izin by id"""
        deleted = delete_jenis_izin(id_jenis_izin)
        if deleted == 0:
            raise NotFoundError("Jenis izin tidak ditemukan")

        return success(message="Jenis izin berhasil dihapus")



# ==================================================
# REF JENIS LEMBUR
# ==================================================
@master_ns.route("/jenis-lembur")
class JenisLemburListResource(Resource):

    @jwt_required()
    @measure_execution_time
    def get(self):
        """Akses: (admin, pegawai), Get list jenis lembur"""
        data = get_jenis_lembur_list()
        return success(data=data, message="List jenis lembur")

    @role_required("admin")
    @master_ns.expect(jenis_lembur_model, validate=True)
    @measure_execution_time
    def post(self):
        """Akses: (admin), Add jenis lembur baru"""
        body = request.get_json(silent=True) or {}

        nama_jenis = body.get("nama_jenis")
        deskripsi = body.get("deskripsi")

        if not nama_jenis:
            raise ValidationError("Nama jenis lembur wajib diisi")

        data = create_jenis_lembur(nama_jenis, deskripsi)
        return success(data=data, message="Jenis lembur berhasil ditambahkan")


@master_ns.route("/jenis-lembur/<int:id_jenis_lembur>")
class JenisLemburDetailResource(Resource):

    @jwt_required()
    @measure_execution_time
    def get(self, id_jenis_lembur):
        """Akses: (admin, pegawai), Get jenis lembur by id"""
        data = get_jenis_lembur_by_id(id_jenis_lembur)
        if not data:
            raise NotFoundError("Jenis lembur tidak ditemukan")

        return success(data=data, message="Detail jenis lembur")

    @role_required("admin")
    @master_ns.expect(jenis_lembur_model, validate=True)
    @measure_execution_time
    def put(self, id_jenis_lembur):
        """Akses: (admin), Edit jenis lembur by id"""
        body = request.get_json(silent=True) or {}

        nama_jenis = body.get("nama_jenis")
        deskripsi = body.get("deskripsi")

        if not nama_jenis:
            raise ValidationError("Nama jenis lembur wajib diisi")

        data = update_jenis_lembur(id_jenis_lembur, nama_jenis, deskripsi)
        if not data:
            raise NotFoundError("Jenis lembur tidak ditemukan")

        return success(data=data, message="Jenis lembur berhasil diperbarui")

    @role_required("admin")
    @measure_execution_time
    def delete(self, id_jenis_lembur):
        """Akses: (admin), Delete jenis lembur by id"""
        deleted = delete_jenis_lembur(id_jenis_lembur)
        if deleted == 0:
            raise NotFoundError("Jenis lembur tidak ditemukan")

        return success(message="Jenis lembur berhasil dihapus")



# ==================================================
# REF LEMBUR RULE
# ==================================================
@master_ns.route("/lembur-rule")
class LemburRuleListResource(Resource):

    @jwt_required()
    @measure_execution_time
    def get(self):
        """Akses: (admin, pegawai), Get list aturan lembur"""
        data = get_lembur_rule_list()
        return success(data=data, message="List rule lembur")

    @role_required("admin")
    @master_ns.expect(lembur_rule_model, validate=True)
    @measure_execution_time
    def post(self):
        """Akses: (admin), Add aturan lembur baru"""
        body = request.get_json(silent=True) or {}

        required_fields = [
            "id_jenis_lembur",
            "urutan_jam",
            "menit_dari",
            "menit_sampai",
            "pengali"
        ]
        for field in required_fields:
            if body.get(field) is None:
                raise ValidationError(f"{field} wajib diisi")

        data = create_lembur_rule(
            body["id_jenis_lembur"],
            body["urutan_jam"],
            body["menit_dari"],
            body["menit_sampai"],
            body["pengali"]
        )

        return success(data=data, message="Rule lembur berhasil ditambahkan")


@master_ns.route("/lembur-rule/<int:id_rule>")
class LemburRuleDetailResource(Resource):

    @jwt_required()
    @measure_execution_time
    def get(self, id_rule):
        """Akses: (admin, pegawai), Get aturan lembur by id"""
        data = get_lembur_rule_by_id(id_rule)
        if not data:
            raise NotFoundError("Rule lembur tidak ditemukan")

        return success(data=data, message="Detail rule lembur")

    @role_required("admin")
    @master_ns.expect(lembur_rule_model, validate=True)
    @measure_execution_time
    def put(self, id_rule):
        """Akses: (admin), Edit aturan lembur by id"""
        body = request.get_json(silent=True) or {}

        required_fields = [
            "id_jenis_lembur",
            "urutan_jam",
            "menit_dari",
            "menit_sampai",
            "pengali"
        ]
        for field in required_fields:
            if body.get(field) is None:
                raise ValidationError(f"{field} wajib diisi")

        data = update_lembur_rule(
            id_rule,
            body["id_jenis_lembur"],
            body["urutan_jam"],
            body["menit_dari"],
            body["menit_sampai"],
            body["pengali"]
        )

        if not data:
            raise NotFoundError("Rule lembur tidak ditemukan")

        return success(data=data, message="Rule lembur berhasil diperbarui")

    @role_required("admin")
    @measure_execution_time
    def delete(self, id_rule):
        """Akses: (admin), Delete aturan lembur by id"""
        deleted = delete_lembur_rule(id_rule)
        if deleted == 0:
            raise NotFoundError("Rule lembur tidak ditemukan")

        return success(message="Rule lembur berhasil dihapus")



# ==================================================
# REF HARI LIBUR
# ==================================================
@master_ns.route("/hari-libur")
class HariLiburListResource(Resource):

    @jwt_required()
    @measure_execution_time
    def get(self):
        """Akses: (admin, pegawai), Get list hari libur"""
        data = get_hari_libur_list()
        return success(data=data, message="List hari libur")

    @role_required("admin")
    @master_ns.expect(hari_libur_model, validate=True)
    @measure_execution_time
    def post(self):
        """Akses: (admin), Add hari libur baru"""
        body = request.get_json(silent=True) or {}

        tanggal = body.get("tanggal")
        nama_libur = body.get("nama_libur")
        jenis = body.get("jenis")

        if not tanggal or not nama_libur or not jenis:
            raise ValidationError(
                "Tanggal, nama libur, dan jenis wajib diisi"
            )

        try:
            tanggal = datetime.strptime(tanggal, "%Y-%m-%d").date()
        except ValueError:
            raise ValidationError("Format tanggal harus YYYY-MM-DD")

        data = create_hari_libur(tanggal, nama_libur, jenis)
        return success(data=data, message="Hari libur berhasil ditambahkan")


@master_ns.route("/hari-libur/<int:id_libur>")
class HariLiburDetailResource(Resource):

    @jwt_required()
    @measure_execution_time
    def get(self, id_libur):
        """Akses: (admin, pegawai), Get hari libur by id"""
        data = get_hari_libur_by_id(id_libur)
        if not data:
            raise NotFoundError("Hari libur tidak ditemukan")

        return success(data=data, message="Detail hari libur")

    @role_required("admin")
    @master_ns.expect(hari_libur_model, validate=True)
    @measure_execution_time
    def put(self, id_libur):
        """Akses: (admin), Edit hari libur by id"""
        body = request.get_json(silent=True) or {}

        tanggal = body.get("tanggal")
        nama_libur = body.get("nama_libur")
        jenis = body.get("jenis")

        if not tanggal or not nama_libur or not jenis:
            raise ValidationError(
                "Tanggal, nama libur, dan jenis wajib diisi"
            )

        try:
            tanggal = datetime.strptime(tanggal, "%Y-%m-%d").date()
        except ValueError:
            raise ValidationError("Format tanggal harus YYYY-MM-DD")

        data = update_hari_libur(
            id_libur, tanggal, nama_libur, jenis
        )
        if not data:
            raise NotFoundError("Hari libur tidak ditemukan")

        return success(data=data, message="Hari libur berhasil diperbarui")

    @role_required("admin")
    @measure_execution_time
    def delete(self, id_libur):
        """Akses: (admin), Delete hari libur by id"""
        deleted = delete_hari_libur(id_libur)
        if deleted == 0:
            raise NotFoundError("Hari libur tidak ditemukan")

        return success(message="Hari libur berhasil dihapus")
