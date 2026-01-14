from flask_restx import Namespace, Resource, fields
from flask import request
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt, get_jwt_identity
from werkzeug.security import check_password_hash, generate_password_hash

# Import local functions and modules
from api.shared.response import success
from api.shared.exceptions import AuthError, ValidationError
from api.utils.decorator import measure_execution_time
from api.query.q_auth import *

auth_ns = Namespace("auth", description="Authentication & Authorization")

admin_login_model = auth_ns.model("AdminLoginRequest", {
        "username": fields.String(required=True, description="Username admin", example="admin"),
        "password": fields.String(required=True, description="Password admin", example="admin123")
    }
)

pegawai_login_model = auth_ns.model("PegawaiLoginRequest", {
        "username": fields.String(required=True, description="Username pegawai", example="pegawai01"),
        "password": fields.String(required=True, description="Password pegawai", example="password123" )
    }
)

change_password_model = auth_ns.model("ChangePasswordRequest", {
        "old_password": fields.String(required=True, description="Password lama", example="passwordlama"),
        "new_password": fields.String(required=True, description="Password baru", example="passwordbaru123")
    }
)

# ================================================
# Fungsi untuk Login dan Logout Admin dan Pegawai
# ================================================
@auth_ns.route("/admin/login")
class AdminLoginResource(Resource):
    
    @auth_ns.expect(admin_login_model, validate=True)
    @measure_execution_time
    def post(self):
        """Akses: (admin), Login Admin Webberkah"""
        body = request.get_json(silent=True) or {}

        username = body.get("username")
        password = body.get("password")

        # validasi input
        if not username or not password:
            raise ValidationError(
                message="Username dan password wajib diisi",
                errors={
                    "username": "required",
                    "password": "required"
                }
            )

        # get data admin
        admin = get_admin_by_username(username)
        if not admin:
            raise AuthError("Username atau password salah")

        if not check_password_hash(admin["password_hash"], password):
            raise AuthError("Username atau password salah")

        # Generate token
        access_token = create_access_token(
            identity=str(admin["id_admin"]),
            additional_claims={
                "account_type": "admin",
                "role": admin["role"]
            }
        )
        refresh_token = create_refresh_token(
        identity=str(admin["id_admin"]),
        additional_claims={
                "role": admin["role"],
                "account_type": "admin"
            }
        )

        # update last login
        update_admin_last_login(admin["id_admin"])

        return success(
            data={
                "access_token": access_token,
                "refresh_token": refresh_token,
                "user": {
                    "id_admin": admin["id_admin"],
                    "username": admin["username"],
                    "role": admin["role"]
                }
            },
            message="Login admin berhasil"
        )



@auth_ns.route("/pegawai/login")
class PegawaiLoginResource(Resource):

    @auth_ns.expect(pegawai_login_model, validate=True)
    @measure_execution_time
    def post(self):
        """Akses: (pegawai), Login Pegawai Webberkah"""

        body = request.get_json(silent=True) or {}

        username = body.get("username")
        password = body.get("password")
        kode_pemulihan = body.get("password")

        # 1️⃣ Validasi input minimum
        if not username:
            raise ValidationError(
                message="Username wajib diisi",
                errors={"username": "required"}
            )

        if not password and not kode_pemulihan:
            raise ValidationError(
                message="Password atau kode pemulihan wajib diisi",
                errors={
                    "password": "required_without:kode_pemulihan",
                    "kode_pemulihan": "required_without:password"
                }
            )

        # 2️⃣ Ambil data pegawai
        pegawai = get_pegawai_by_username(username)
        if not pegawai:
            raise AuthError("Username tidak terdaftar")

        if pegawai["pegawai_status"] != 1:
            raise AuthError("Pegawai tidak aktif")

        # 3️⃣ Validasi kredensial
        authenticated = False

        # ➤ Login dengan password
        if password and check_password_hash(pegawai["password_hash"], password):
            authenticated = True

        # ➤ Fallback login dengan kode pemulihan
        elif kode_pemulihan and pegawai["kode_pemulihan"]:
            if kode_pemulihan == pegawai["kode_pemulihan"]:
                authenticated = True

        if not authenticated:
            raise AuthError("Kredensial tidak valid")

        # 4️⃣ Generate token
        access_token = create_access_token(
            identity=str(pegawai["id_pegawai"]),
            additional_claims={"account_type": "pegawai"}
        )

        refresh_token = create_refresh_token(
            identity=str(pegawai["id_pegawai"]),
            additional_claims={"account_type": "pegawai"}
        )

        # 5️⃣ Update last login
        update_pegawai_last_login(pegawai["id_auth_pegawai"])

        return success(
            message="Login pegawai berhasil",
            data={
                "access_token": access_token,
                "refresh_token": refresh_token,
                "user": {
                    "id_pegawai": pegawai["id_pegawai"],
                    "username": pegawai["username"],
                    "img_path": pegawai["img_path"]
                }
            }
        )
        
        
@auth_ns.route("/logout")
class LogoutResource(Resource):

    @jwt_required()
    @measure_execution_time
    def post(self):
        """Akses: (admin, pegawai), Logout user"""
        # JWT stateless → logout cukup di frontend
        user_id = get_jwt_identity()
        return success(
            data={
                "id": user_id
            },
            message="Logout berhasil"
        )


# ======================================
# Endpoint get data user sedang login
# ======================================
@auth_ns.route("/me")
class MeResource(Resource):

    @jwt_required()
    @measure_execution_time
    def get(self):
        """Akses: (admin, pegawai), Ambil data user sedang login"""
        jwt_data = get_jwt()
        identity = get_jwt_identity()

        return success(
            data={
                "id": identity,
                "account_type": jwt_data.get("account_type"),
                "role": jwt_data.get("role"),
                "token_type": "access"
            },
            message="Data user berhasil diambil"
        )


# ======================================
# Endpoint refresh token
# ======================================
@auth_ns.route("/refresh")
class RefreshTokenResource(Resource):

    @jwt_required(refresh=True)
    @measure_execution_time
    def post(self):
        """Akses: (admin, pegawai), Refresh access token menggunakan refresh token"""
        # ambil data dari JWT
        identity = get_jwt_identity()
        jwt_data = get_jwt()

        account_type = jwt_data.get("account_type")
        role = jwt_data.get("role")

        if not account_type:
            raise AuthError("Token tidak valid")

        # generate token baru
        new_access_token = create_access_token(
            identity=str(identity),
            additional_claims={
                "account_type": account_type,
                "role": role
            }
        )

        return success(
            data={
                "access_token": new_access_token
            },
            message="Access token berhasil diperbarui"
        )


# ======================================
# Endpoint untuk ganti password
# ======================================
@auth_ns.route("/change-password")
class ChangePasswordResource(Resource):
    
    @auth_ns.expect(change_password_model, validate=True)
    @jwt_required()
    @measure_execution_time
    def put(self):
        """Akses: (admin, pegawai), Ganti password user sedang login"""
        body = request.get_json(silent=True) or {}

        old_password = body.get("old_password")
        new_password = body.get("new_password")

        if not old_password or not new_password:
            raise ValidationError(
                message="Password lama dan password baru wajib diisi"
            )

        identity = get_jwt_identity()
        jwt_data = get_jwt()
        account_type = jwt_data.get("account_type")

        # ambil password lama
        if account_type == "admin":
            old_hash = get_admin_password(identity)
        elif account_type == "pegawai":
            old_hash = get_pegawai_password(identity)
        else:
            raise AuthError("Account type tidak valid")

        if not old_hash or not check_password_hash(old_hash, old_password):
            raise AuthError("Password lama tidak sesuai")

        # update password baru
        new_hash = generate_password_hash(new_password, method="pbkdf2:sha256")

        if account_type == "admin":
            update_admin_password(identity, new_hash)
        else:
            update_pegawai_password(identity, new_hash)

        return success(
            message="Password berhasil diubah"
        )