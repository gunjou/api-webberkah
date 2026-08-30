# api/__init__.py
import os
from datetime import timedelta
from flask import Flask
from flask_cors import CORS
from flask_restx import Api
from dotenv import load_dotenv
from flask_jwt_extended import JWTManager
from jwt.exceptions import ExpiredSignatureError

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
from api.hutang import hutang_ns
from api.payroll import payroll_ns
from api.leaderboard import leaderboard_ns

from api.cashbook.account import ns as account_ns
from api.cashbook.category import ns as category_ns
from api.cashbook.transaction import ns as transaction_ns
from api.cashbook.opening_balance import ns as opening_balance_ns
from api.cashbook.dashboard import ns as cashbook_dashboard_ns

from api.work_item.master import ns as work_item_master_ns

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

jwt = JWTManager(app)

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
api.add_namespace(hutang_ns, path="/hutang")
api.add_namespace(payroll_ns, path="/payroll")
api.add_namespace(leaderboard_ns, path="/leaderboard")

api.add_namespace(account_ns, path="/cashbook/accounts")
api.add_namespace(category_ns, path="/cashbook/categories")
api.add_namespace(transaction_ns, path="/cashbook/transactions")
api.add_namespace(opening_balance_ns, path="/cashbook/opening-balance")
api.add_namespace(cashbook_dashboard_ns, path="/cashbook/dashboard")

api.add_namespace(work_item_master_ns, path="/work-item/master")


# ==============================
# JWT ERROR HANDLERS
# ==============================
@jwt.expired_token_loader
def expired_token_callback(jwt_header, jwt_payload):
    return {
        "success": False,
        "message": "Token expired",
        "code": "TOKEN_EXPIRED"
    }, 401


@jwt.invalid_token_loader
def invalid_token_callback(error):
    return {
        "success": False,
        "message": "Token tidak valid",
        "code": "INVALID_TOKEN"
    }, 401


@jwt.unauthorized_loader
def missing_token_callback(error):
    return {
        "success": False,
        "message": "Token tidak ditemukan",
        "code": "TOKEN_MISSING"
    }, 401


@jwt.revoked_token_loader
def revoked_token_callback(jwt_header, jwt_payload):
    return {
        "success": False,
        "message": "Token telah dicabut",
        "code": "TOKEN_REVOKED"
    }, 401


@app.errorhandler(ExpiredSignatureError)
def handle_expired_signature(error):
    return {
        "success": False,
        "message": "Token expired",
        "code": "TOKEN_EXPIRED"
    }, 401


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
