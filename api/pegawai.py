from datetime import datetime
from flask import request
from flask_restx import Namespace, Resource, fields, reqparse
from flask_jwt_extended import jwt_required
from werkzeug.security import generate_password_hash
from werkzeug.datastructures import FileStorage

from api.shared.exceptions import NotFoundError, ValidationError
from api.shared.helper import generate_recovery_code
from api.shared.response import success
from api.utils.decorator import measure_execution_time, role_required
from api.query.q_pegawai import *


pegawai_ns = Namespace("pegawai", description="Manajemen Pegawai")


pegawai_register_model = pegawai_ns.model(
    "PegawaiRegister",
    {
        "nama_lengkap": fields.String(required=True),
        "nip": fields.String(required=True),
        "username": fields.String(required=True),
        "password": fields.String(required=True),
        "tanggal_masuk": fields.String(required=True, example="2026-01-09"),
        "jenis_kelamin": fields.String(required=True, example="L"),
        "id_departemen": fields.Integer(required=True),
        "id_jabatan": fields.Integer(required=True),
        "id_status_pegawai": fields.Integer(required=True),
    }
)

pegawai_update_lengkap_model = pegawai_ns.model("PegawaiUpdateLengkap", {
        "nip": fields.String(required=True, description="NIP pegawai"),
        "nama_lengkap": fields.String(required=True, description="Nama lengkap pegawai"),
        "nama_panggilan": fields.String(required=True, description="Nama panggilan"),
        "jenis_kelamin": fields.String(required=True, description="Jenis kelamin (L/P)"),
        "tanggal_masuk": fields.String(required=True, description="Tanggal masuk (YYYY-MM-DD)"),
        "id_departemen": fields.Integer(required=True, description="ID departemen"),
        "id_jabatan": fields.Integer(required=True, description="ID jabatan"),
        "id_level_jabatan": fields.Integer(required=True, description="ID level jabatan"),
        "id_status_pegawai": fields.Integer(required=True, description="ID status pegawai"),

        # Table pegawai pribadi
        "nik": fields.String(required=False, description="NIK (5201xxxxxxxxxxxx)"),
        "tempat_lahir": fields.String(required=False, description="Tempat lahir (Perampuan)"),
        "tanggal_lahir": fields.String(required=False, description="Tanggal lahir (YYYY-MM-DD)"),
        "agama": fields.String(required=False, description="Agama (Islam, Kristen, Hindu, Buddha, dll)"),
        "status_nikah": fields.String(required=False, description="Status pernikahan (Belum Menikah, Menikah)"),
        "alamat": fields.String(required=False, description="Alamat"),
        "no_telepon": fields.String(required=False, description="Nomor telepon (0812xxxx)"),
        "email_pribadi": fields.String(required=False, description="Email pribadi"),
    }
)

pegawai_rekening_model = pegawai_ns.model("PegawaiRekening", {
        "nama_bank": fields.String(required=True, description="Nama bank (BRI, BCA, MANDIRI, DLL)"),
        "no_rekening": fields.String(required=True, description="Nomor rekening"),
        "atas_nama": fields.String(required=True, description="Atas nama rekening")
    }
)

pegawai_pendidikan_model = pegawai_ns.model("PegawaiPendidikan", {
        "jenjang": fields.String(required=True, description="Jenjang pendidikan"),
        "institusi": fields.String(required=True, description="Institusi pendidikan"),
        "jurusan": fields.String(required=True, description="Jurusan"),
        "tahun_masuk": fields.Integer(required=False, description="Tahun masuk"),
        "tahun_lulus": fields.Integer(required=False, description="Tahun lulus")
    }
)

upload_face_parser = reqparse.RequestParser()
upload_face_parser.add_argument("file", type=FileStorage, location="files", required=True, help="File gambar wajah")

pegawai_reset_password_model = pegawai_ns.model("PegawaiResetPassword", {
        "password_baru": fields.String(required=True, description="Password baru pegawai", example="123456")
    }
)

pegawai_lokasi_model = pegawai_ns.model("PegawaiLokasiAbsensi", {
        "id_lokasi_list": fields.List(fields.Integer, required=True, description="List ID lokasi absensi", example=[1, 3])
    }
)



# ==================================================
# ALL DATA PEGAWAI
# ==================================================
@pegawai_ns.route("/all-data")
class PegawaiListResource(Resource):

    @role_required("admin")
    @measure_execution_time
    def get(self):
        """Akses: (admin), Get semua data pegawai lengkap --> admin/pegawai"""
        rows = get_all_pegawai_core()
        result = []

        for row in rows:
            pegawai = {
                "id_pegawai": row["id_pegawai"],
                "nip": row["nip"],
                "nama_lengkap": row["nama_lengkap"],
                "nama_panggilan": row["nama_panggilan"],
                "jenis_kelamin": row["jenis_kelamin"],
                "tanggal_masuk": row["tanggal_masuk"].strftime('%d-%m-%Y') if row["tanggal_masuk"] else "-",

                "id_departemen": row["id_departemen"],
                "departemen": row["nama_departemen"],
                "id_jabatan": row["id_jabatan"],
                "jabatan": row["nama_jabatan"],
                "id_level_jabatan": row["id_level_jabatan"],
                "level_jabatan": row["level_jabatan"],
                "id_status_pegawai": row["id_status_pegawai"],
                "status_pegawai": row["status_pegawai"],

                "pribadi": {
                    "nik": row["nik"],
                    "alamat": row["alamat"],
                    "no_telepon": row["no_telepon"],
                    "email": row["email_pribadi"],
                    "tempat_lahir": row["tempat_lahir"],
                    "tanggal_lahir": row["tanggal_lahir"],
                    "image": row["image_path"],
                    "agama": row["agama"],
                    "status_nikah": row["status_nikah"],
                },

                "rekening": {
                    "bank": row["nama_bank"],
                    "nomor": row["no_rekening"],
                    "an": row["atas_nama"],
                },

                "auth_pegawai": {
                    "username": row["username"],
                    "recovery_code": row["kode_pemulihan"],
                    "img_path": row["img_path"],
                    "status": row["auth_status"],
                    "last_login_at": (
                        row["last_login_at"].strftime("%d-%m-%Y %H:%M:%S")
                        if row["last_login_at"] is not None
                        else None
                    ),
                },

                "pendidikan": get_pendidikan_by_pegawai(row["id_pegawai"]),
                "lokasi_absensi": get_lokasi_absensi_by_pegawai(row["id_pegawai"]),
            }

            result.append(pegawai)

        return success(
            data=result,
            message="List pegawai lengkap",
            meta={"total": len(result)}
        )


# ==================================================
# GET DATA PEGAWAI PER TAB
# ==================================================
@pegawai_ns.route("/profile")
class PegawaiProfileListResource(Resource):

    @role_required("admin")
    @measure_execution_time
    def get(self):
        """(admin) Get list profile pegawai (CORE TAB)"""
        rows = get_pegawai_profile()
        result = []

        for row in rows:
            result.append({
                "id_pegawai": row["id_pegawai"],
                "nip": row["nip"],
                "nama_lengkap": row["nama_lengkap"],
                "nama_panggilan": row["nama_panggilan"],
                "jenis_kelamin": row["jenis_kelamin"],
                "tanggal_masuk": row["tanggal_masuk"],

                "id_status_pegawai": row["id_status_pegawai"],
                "status_pegawai": row["status_pegawai"],
                "id_jabatan": row["id_jabatan"],
                "jabatan": row["nama_jabatan"],
                "id_departemen": row["id_departemen"],
                "departemen": row["nama_departemen"],
                "id_level_jabatan": row["id_level_jabatan"],
                "level_jabatan": row["level_jabatan"],

                "nik": row["nik"],
                "agama": row["agama"],
                "tempat_lahir": row["tempat_lahir"],
                "tanggal_lahir": row["tanggal_lahir"],
                "status_nikah": row["status_nikah"],

                "email": row["email_pribadi"],
                "no_telepon": row["no_telepon"],
                "alamat": row["alamat"],
            })

        return success(
            data=result,
            message="List profile pegawai",
            meta={"total": len(result)}
        )


@pegawai_ns.route("/rekening")
class PegawaiRekeningListResource(Resource):

    @role_required("admin")
    @measure_execution_time
    def get(self):
        """(admin) Get data rekening pegawai (TAB REKENING)"""
        rows = get_pegawai_rekening()
        result = []

        for row in rows:
            result.append({
                "id_pegawai": row["id_pegawai"],
                "nip": row["nip"],
                "nama_lengkap": row["nama_lengkap"],
                "tanggal_masuk": row["tanggal_masuk"],
                "status_pegawai": row["status_pegawai"],

                "nama_bank": row["nama_bank"],
                "no_rekening": row["no_rekening"],
                "atas_nama": row["atas_nama"],
                
            })

        return success(
            data=result,
            message="List data rekening pegawai",
            meta={"total": len(result)}
        )


@pegawai_ns.route("/pendidikan")
class PegawaiPendidikanListResource(Resource):

    @role_required("admin")
    @measure_execution_time
    def get(self):
        """(admin) Get data pendidikan pegawai (TAB PENDIDIKAN)"""
        rows = get_pegawai_pendidikan()
        result = []

        for row in rows:
            result.append({
                "id_pegawai": row["id_pegawai"],
                "nip": row["nip"],
                "nama_lengkap": row["nama_lengkap"],
                "tanggal_masuk": row["tanggal_masuk"],
                "status_pegawai": row["status_pegawai"],

                "jenjang": row["jenjang"],
                "institusi": row["institusi"],
                "jurusan": row["jurusan"],
                "tahun_masuk": row["tahun_masuk"],
                "tahun_lulus": row["tahun_lulus"],
            })

        return success(
            data=result,
            message="List data pendidikan pegawai",
            meta={"total": len(result)}
        )


@pegawai_ns.route("/akun")
class PegawaiAkunListResource(Resource):

    @role_required("admin")
    @measure_execution_time
    def get(self):
        """(admin) Get data akun sistem pegawai (TAB AKUN)"""
        rows = get_pegawai_akun()
        result = []

        for row in rows:
            result.append({
                "id_pegawai": row["id_pegawai"],
                "nip": row["nip"],
                "nama_lengkap": row["nama_lengkap"],
                "tanggal_masuk": row["tanggal_masuk"],
                "status_pegawai": row["status_pegawai"],

                "username": row["username"],
                "kode_pemulihan": row["kode_pemulihan"],
                "img_path": row["img_path"],
                "last_login_at": (
                    row["last_login_at"].strftime("%d-%m-%Y %H:%M:%S")
                    if row["last_login_at"] else None
                ),
                "status": row["auth_status"],
            })

        return success(
            data=result,
            message="List data akun sistem pegawai",
            meta={"total": len(result)}
        )


@pegawai_ns.route("/lokasi")
class PegawaiLokasiListResource(Resource):

    @role_required("admin")
    @measure_execution_time
    def get(self):
        """(admin) Get data lokasi absensi pegawai (TAB LOKASI)"""
        rows = get_pegawai_lokasi()
        result_map = {}

        for row in rows:
            pid = row["id_pegawai"]

            if pid not in result_map:
                result_map[pid] = {
                    "id_pegawai": row["id_pegawai"],
                    "nip": row["nip"],
                    "nama_lengkap": row["nama_lengkap"],
                    "tanggal_masuk": (
                        row["tanggal_masuk"].strftime("%d-%m-%Y")
                        if row["tanggal_masuk"] else None
                    ),
                    "status_pegawai": row["status_pegawai"],
                    "lokasi_absensi": []
                }

            # jika pegawai punya lokasi
            if row["id_lokasi"]:
                result_map[pid]["lokasi_absensi"].append({
                    "id_lokasi": row["id_lokasi"],
                    "nama_lokasi": row["nama_lokasi"],
                    "latitude": row["latitude"],
                    "longitude": row["longitude"],
                    "radius_meter": row["radius_meter"],
                })

        result = list(result_map.values())

        return success(
            data=result,
            message="List data lokasi absensi pegawai",
            meta={"total": len(result)}
        )



# ==================================================
# REGISTER PEGAWAI BARU
# ==================================================
@pegawai_ns.route("/register")
class PegawaiRegisterResource(Resource):

    @role_required("admin")
    @pegawai_ns.expect(pegawai_register_model, validate=True)
    @measure_execution_time
    def post(self):
        """Akses: (admin), Tambah pegawai baru --> admin/pegawai"""
        body = request.get_json(silent=True) or {}

        # basic validation
        required_fields = [
            "nama_lengkap",
            "nip",
            "username",
            "password",
            "tanggal_masuk",
            "jenis_kelamin",
            "id_departemen",
            "id_jabatan",
            "id_level_jabatan",
            "id_status_pegawai"
        ]

        for field in required_fields:
            if not body.get(field):
                raise ValidationError(f"{field} wajib diisi")

        if is_nip_exists(body["nip"]):
            raise ValidationError("NIP sudah terdaftar")

        if is_username_exists(body["username"]):
            raise ValidationError("Username sudah digunakan")

        try:
            tanggal_masuk = datetime.strptime(
                body["tanggal_masuk"], "%Y-%m-%d"
            ).date()
        except ValueError:
            raise ValidationError("Format tanggal_masuk harus YYYY-MM-DD")

        password_hash = generate_password_hash(body["password"], method="pbkdf2:sha256")
        # generate recovery code di backend
        kode_pemulihan = generate_recovery_code(6)


        id_pegawai = register_pegawai(
            nama_lengkap=body["nama_lengkap"].title(),
            nip=body["nip"],
            jenis_kelamin=body["jenis_kelamin"],
            tanggal_masuk=tanggal_masuk,
            id_departemen=body["id_departemen"],
            id_jabatan=body["id_jabatan"],
            id_level_jabatan=body["id_level_jabatan"],
            id_status_pegawai=body["id_status_pegawai"],
            username=body["username"].lower(),
            password_hash=password_hash,
            kode_pemulihan=kode_pemulihan
        )

        return success(
            data={"id_pegawai": id_pegawai},
            message="Pegawai berhasil didaftarkan"
        )



# ==================================================
# UPDATE DAN INSERT DATA PEGAWAI PRIBADI
# ==================================================
@pegawai_ns.route("/update-lengkap/<int:id_pegawai>")
class PegawaiUpdateLengkapResource(Resource):

    @role_required("admin")
    @pegawai_ns.expect(pegawai_update_lengkap_model, validate=True)
    @measure_execution_time
    def put(self, id_pegawai):
        """Akses: (admin), Update data pegawai lengkap (pegawai & pribadi) --> admin/data-pegawai"""
        body = request.get_json(silent=True) or {}

        if not is_pegawai_exists(id_pegawai):
            raise NotFoundError("Pegawai tidak ditemukan")

        try:
            tanggal_masuk = datetime.strptime(
                body.get("tanggal_masuk"), "%Y-%m-%d"
            ).date()

            tanggal_lahir = (
                datetime.strptime(body["tanggal_lahir"], "%Y-%m-%d").date()
                if body.get("tanggal_lahir")
                else None
            )
        except ValueError:
            raise ValidationError("Format tanggal harus YYYY-MM-DD")

        pegawai_data = {
            "nip": body.get("nip"),
            "nama_lengkap": body.get("nama_lengkap").title(),
            "nama_panggilan": body.get("nama_panggilan").title(),
            "jenis_kelamin": body.get("jenis_kelamin"),
            "tanggal_masuk": tanggal_masuk,
            "id_departemen": body.get("id_departemen"),
            "id_jabatan": body.get("id_jabatan"),
            "id_level_jabatan": body.get("id_level_jabatan"),
            "id_status_pegawai": body.get("id_status_pegawai"),
        }

        pribadi_data = {
            "nik": body.get("nik"),
            "alamat": body.get("alamat").title(),
            "no_telepon": body.get("no_telepon"),
            "email_pribadi": body.get("email_pribadi"),
            "tempat_lahir": body.get("tempat_lahir").title(),
            "tanggal_lahir": tanggal_lahir,
            "agama": body.get("agama").title(),
            "status_nikah": body.get("status_nikah").title(),
        }

        update_pegawai_lengkap(
            id_pegawai=id_pegawai,
            pegawai_data=pegawai_data,
            pribadi_data=pribadi_data
        )

        return success(
            message="Data pegawai berhasil diperbarui"
        )



# ==================================================
# UPDATE DAN INSERT REKENING PEGAWAI
# ==================================================
@pegawai_ns.route("/update-rekening/<int:id_pegawai>")
class PegawaiUpdateRekeningResource(Resource):

    @role_required("admin")
    @pegawai_ns.expect(pegawai_rekening_model, validate=True)
    @measure_execution_time
    def put(self, id_pegawai):
        """Akses: (admin), Update data rekening pegawai (pegawai_rekening) --> admin/rekening-bank"""
        body = request.get_json(silent=True) or {}

        if not is_pegawai_exists(id_pegawai):
            raise NotFoundError("Pegawai tidak ditemukan")

        nama_bank = body.get("nama_bank")
        no_rekening = body.get("no_rekening")
        atas_nama = body.get("atas_nama").title()

        if not nama_bank or not no_rekening or not atas_nama:
            raise ValidationError(
                "Nama bank, nomor rekening, dan atas nama wajib diisi"
            )

        upsert_pegawai_rekening(
            id_pegawai=id_pegawai,
            nama_bank=nama_bank,
            no_rekening=no_rekening,
            atas_nama=atas_nama
        )

        return success(
            message="Data rekening pegawai berhasil diperbarui"
        )



# ==================================================
# UPDATE DAN INSERT PEDIDIKAN PEGAWAI
# ==================================================
@pegawai_ns.route("/update-pendidikan/<int:id_pegawai>")
class PegawaiUpdatePendidikanResource(Resource):

    @role_required("admin")
    @pegawai_ns.expect(pegawai_pendidikan_model, validate=True)
    @measure_execution_time
    def put(self, id_pegawai):
        """Akses: (admin), Update data pendidikan pegawai (pegawai_pendidikan) --> admin/pendidikan"""
        body = request.get_json(silent=True) or {}

        if not is_pegawai_exists(id_pegawai):
            raise NotFoundError("Pegawai tidak ditemukan")

        jenjang = body.get("jenjang")
        institusi = body.get("institusi").title()
        jurusan = body.get("jurusan").title()

        if not jenjang or not institusi or not jurusan:
            raise ValidationError(
                "Jenjang, institusi, dan jurusan wajib diisi"
            )

        tahun_masuk = body.get("tahun_masuk")
        tahun_lulus = body.get("tahun_lulus")

        # optional sanity check
        if tahun_masuk and tahun_lulus and tahun_lulus < tahun_masuk:
            raise ValidationError(
                "Tahun lulus tidak boleh lebih kecil dari tahun masuk"
            )

        upsert_pegawai_pendidikan(
            id_pegawai=id_pegawai,
            jenjang=jenjang,
            institusi=institusi,
            jurusan=jurusan,
            tahun_masuk=tahun_masuk,
            tahun_lulus=tahun_lulus
        )

        return success(
            message="Data pendidikan pegawai berhasil diperbarui"
        )



# ==================================================
# UPDATE WAJAH PEGAWAI UNTUK VERIFIKASI ABSENSI
# ==================================================
@pegawai_ns.route("/update-wajah/<int:id_pegawai>")
class PegawaiUpdateWajahResource(Resource):

    @role_required("admin")
    @pegawai_ns.expect(upload_face_parser)
    @measure_execution_time
    def put(self, id_pegawai):
        """Akses: (admin), Update data wajah pegawai (auth_pegawai) --> admin/akun-sistem"""
        if not is_pegawai_exists(id_pegawai):
            raise NotFoundError("Pegawai tidak ditemukan")

        args = upload_face_parser.parse_args()
        file = args.get("file")

        img_url = enroll_face_pegawai(
            id_pegawai=id_pegawai,
            file=file
        )

        return success(
            data={
                "img_path": img_url
            },
            message="Wajah pegawai berhasil diperbarui"
        )



# ==================================================
# RESET PASSWORD PEGAWAI LANGSUNG OLEH ADMIN
# ==================================================
@pegawai_ns.route("/reset-password/<int:id_pegawai>")
class PegawaiResetPasswordResource(Resource):

    @role_required("admin")
    @pegawai_ns.expect(pegawai_reset_password_model, validate=True)
    @measure_execution_time
    def put(self, id_pegawai):
        """Akses: (admin), reset password pegawai (auth_pegawai) --> admin/akun-sistem"""
        body = request.get_json(silent=True) or {}

        if not is_pegawai_exists(id_pegawai):
            raise NotFoundError("Pegawai tidak ditemukan")

        auth = get_auth_pegawai_by_pegawai_id(id_pegawai)
        if not auth:
            raise NotFoundError("Akun pegawai belum tersedia")

        password_baru = body.get("password_baru")
        if not password_baru:
            raise ValidationError("Password baru wajib diisi")

        # hash password baru
        password_hash = generate_password_hash(password_baru, method="pbkdf2:sha256")

        updated = reset_password_pegawai(
            id_pegawai=id_pegawai,
            password_hash=password_hash
        )

        if updated == 0:
            raise ValidationError("Gagal mereset password pegawai")

        return success(
            message="Password pegawai berhasil direset"
        )



# ==================================================
# SINKRONISASI LOKASI ABSENSI PEGAWAI
# ==================================================
@pegawai_ns.route("/update-lokasi/<int:id_pegawai>")
class PegawaiUpdateLokasiResource(Resource):

    @role_required("admin")
    @pegawai_ns.expect(pegawai_lokasi_model, validate=True)
    @measure_execution_time
    def put(self, id_pegawai):
        """Akses: (admin), sinkronisasi lokasi absensi pegawai (pegawai_lokasi) --> admin/lokasi-absensi"""
        body = request.get_json(silent=True) or {}

        if not is_pegawai_exists(id_pegawai):
            raise NotFoundError("Pegawai tidak ditemukan")

        id_lokasi_list = body.get("id_lokasi_list")
        if not isinstance(id_lokasi_list, list):
            raise ValidationError("id_lokasi_list harus berupa array")

        # opsional: hapus duplikat
        id_lokasi_list = list(set(id_lokasi_list))

        sync_lokasi_pegawai(
            id_pegawai=id_pegawai,
            id_lokasi_list=id_lokasi_list
        )

        return success(
            message="Lokasi absensi pegawai berhasil diperbarui"
        )



# ==================================================
# NONAKTIFKAN PEGAWAI & NONAKTIFKAN AKUN LOGIN
# ==================================================
@pegawai_ns.route("/delete/<int:id_pegawai>")
class PegawaiDeleteResource(Resource):

    @role_required("admin")
    @measure_execution_time
    def delete(self, id_pegawai):
        """Akses: (admin), delete data pegawai (pegawai) --> admin/pegawai"""
        if not is_pegawai_exists(id_pegawai):
            raise NotFoundError("Pegawai tidak ditemukan")

        deleted = soft_delete_pegawai(id_pegawai)
        if deleted == 0:
            raise NotFoundError("Pegawai sudah tidak aktif")

        return success(
            message="Pegawai berhasil dinonaktifkan"
        )
