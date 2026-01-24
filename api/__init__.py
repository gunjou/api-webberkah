import os
from datetime import timedelta
from flask import Flask
from flask_cors import CORS
from flask_restx import Api
from dotenv import load_dotenv
from flask_jwt_extended import JWTManager

from api.shared.exceptions import AppError

# === Load ENV ===
load_dotenv()

from api.auth import auth_ns
from api.master import master_ns
from api.export import export_ns
from api.pegawai import pegawai_ns
from api.absensi import absensi_ns
from api.perizinan import perizinan_ns
from api.presensi import presensi_ns
from api.lembur import lembur_ns
from api.dashboard import dashboard_ns

app = Flask(__name__)
CORS(app)

# ==============================
# JWT CONFIG
# ==============================
app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY")
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(
    minutes=int(os.getenv("JWT_ACCESS_EXPIRES", 60))
)
app.config["JWT_REFRESH_TOKEN_EXPIRES"] = timedelta(
    days=int(os.getenv("JWT_REFRESH_EXPIRES", 7))
)

JWTManager(app)

# ==============================
# SWAGGER AUTH CONFIG
# ==============================
authorizations = {
    "Bearer Auth": {
        "type": "apiKey",
        "in": "header",
        "name": "Authorization",
        "description": "Gunakan format: **Bearer &lt;JWT&gt;**"
    }
}

# ==============================
# FLASK RESTX API
# ==============================
api = Api(
    app,
    version="2.0",
    title="Webberkah API",
    description="HRIS Backend Webberkah v2",
    doc="/docs",
    prefix="/",
    authorizations=authorizations,
    security="Bearer Auth"
)

# ==============================
# REGISTER NAMESPACES
# ==============================
api.add_namespace(auth_ns, path="/auth")
api.add_namespace(master_ns, path="/master")
api.add_namespace(export_ns, path="/export")
api.add_namespace(pegawai_ns, path="/pegawai")
api.add_namespace(absensi_ns, path="/absensi")
api.add_namespace(perizinan_ns, path="/perizinan")
api.add_namespace(presensi_ns, path="/presensi")
api.add_namespace(lembur_ns, path="/lembur")
api.add_namespace(dashboard_ns, path="/dashboard")


# ==============================
# GLOBAL ERROR HANDLER
# ==============================
@api.errorhandler(AppError)
def handle_app_error_restx(error: AppError):
    return {
        "success": False,
        "message": error.message,
        "code": error.status_code,
        "errors": error.errors
    }, error.status_code

# @api.errorhandler(Exception)
# def handle_unexpected_error_restx(error):
#     # log error kalau mau
#     return {
#         "success": False,
#         "message": "Internal server error",
#         "code": "INTERNAL_ERROR"
#     }, 500
