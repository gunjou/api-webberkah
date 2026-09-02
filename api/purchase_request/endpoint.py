# api/purchase_request/endpoint.py

import json

from flask import request, send_file
from flask_jwt_extended import get_jwt_identity, jwt_required, get_jwt
from flask_restx import Resource, fields

from api.shared.response import success
from api.shared.exceptions import ValidationError
from api.utils.decorator import measure_execution_time

from . import ns
from .service import *


# ======================= #ANCHOR - SWAGGER MODEL ============================ #

purchase_request_create_model = ns.model(
    "PurchaseRequestCreate", {
        "tanggal_request": fields.String(required=False, description="Request Date (YYYY-MM-DD)"),
        "id_departemen": fields.Integer(required=True, description="Department ID"),
        "nama_pekerjaan": fields.String(required=True, description="Job Name"),
        "priority": fields.String(required=False, default="NORMAL", enum=["NORMAL", "URGENT", "TOP_URGENT"], description="Request Priority"),
        "note": fields.String(required=False, description="Request Note"),
        "items": fields.List(
            fields.Nested(
                ns.model(
                    "PurchaseRequestItemCreate", {
                        "keterangan": fields.String(required=True, description="Item Description"),
                        "unit": fields.String(required=True, description="Unit"),
                        "harga_satuan": fields.Float(required=True, description="Unit Price"),
                        "jumlah": fields.Float(required=True, description="Quantity")
                    }
                )
            ),
            required=True,
            description="Purchase Request Items"
        ),
        "payment_description": fields.String(required=False, description="Payment Description"),
        "payment_bank": fields.String(required=False, description="Bank Name"),
        "payment_account_number": fields.String(required=False, description="Bank Account Number"),
        "payment_account_name": fields.String(required=False, description="Bank Account Name"),
        "attachment_name": fields.String(required=False, description="Attachment File Name"),
        "attachment_path": fields.String(required=False, description="Attachment CDN URL")
    }
)

purchase_request_update_model = ns.model(
    "PurchaseRequestUpdate", {
        "tanggal_request": fields.String(required=False, description="Request Date (YYYY-MM-DD)"),
        "id_departemen": fields.Integer(required=False, description="Department ID"),
        "nama_pekerjaan": fields.String(required=False, description="Job Name"),
        "priority": fields.String(required=False, description="Request Priority", enum=["NORMAL", "URGENT", "TOP_URGENT"]),
        "note": fields.String(required=False, description="Request Note"),
        "items": fields.List(
            fields.Nested(
                ns.model(
                    "PurchaseRequestUpdateItem", {
                        "item_no": fields.Integer(required=True, description="Item Number"),
                        "keterangan": fields.String(required=True, description="Item Description"),
                        "unit": fields.String(required=True, description="Unit"),
                        "harga_satuan": fields.Float(required=True, description="Unit Price"),
                        "jumlah": fields.Float(required=True, description="Quantity")
                    }
                )
            ),
            required=False,
            description="Purchase Items"
        ),
        "payment_description": fields.String(required=False, description="Payment Description"),
        "payment_bank": fields.String(required=False, description="Bank Name"),
        "payment_account_number": fields.String(required=False, description="Bank Account Number"),
        "payment_account_name": fields.String(required=False, description="Bank Account Name"),
        "attachment_name": fields.String(required=False, description="Attachment File Name"),
        "attachment_path": fields.String(required=False, description="Attachment CDN URL")
    }
)

purchase_request_review_model = ns.model(
    "PurchaseRequestReview", {
        "note": fields.String(required=False, description="Review Note")
    }
)

purchase_request_approve_model = ns.model(
    "PurchaseRequestApprove", {
        "note": fields.String(required=False, description="Approval Note")
    }
)

purchase_request_reject_model = ns.model(
    "PurchaseRequestReject", {
        "note": fields.String(required=True, description="Reject Reason")
    }
)

purchase_request_paid_model = ns.model(
    "PurchaseRequestPaid", {
        "note": fields.String(required=False, description="Payment Note")
    }
)


# ========================== #ANCHOR - SWAGGER PARSER ======================== #

purchase_request_filter_parser = ns.parser()
purchase_request_filter_parser.add_argument(
    "status",
    type=str,
    required=False,
    choices=("ACTIVE", "REQUESTED", "REVIEWED", "APPROVED", "REJECTED", "PAID"),
    location="args",
    default="ACTIVE",
    help=(
        "Request Status. "
        "ACTIVE = REQUESTED, REVIEWED, APPROVED"
    )
)
purchase_request_filter_parser.add_argument("id_departemen", type=int, required=False, location="args", help="Department ID")
purchase_request_filter_parser.add_argument("tanggal_mulai", type=str, required=False, location="args", help="Start Date (YYYY-MM-DD)")
purchase_request_filter_parser.add_argument("tanggal_selesai", type=str, required=False, location="args", help="End Date (YYYY-MM-DD)")


purchase_request_history_parser = ns.parser()
purchase_request_history_parser.add_argument("status", required=False, default="PAID", choices=("PAID", "REJECTED"), location="args", help="History Status")
purchase_request_history_parser.add_argument("id_departemen", required=False, location="args", help="Department ID")
purchase_request_history_parser.add_argument("tanggal_mulai", required=False, location="args", help="Start Date (YYYY-MM-DD)")
purchase_request_history_parser.add_argument("tanggal_selesai", required=False, location="args", help="End Date (YYYY-MM-DD)")
purchase_request_history_parser.add_argument("page", required=False, default=1, location="args", help="Page number")
purchase_request_history_parser.add_argument("per_page", required=False, default=10, location="args", help="Data per page")


# ============================================================================ #
#                 #SECTION - PURCHASE REQUEST OPERATION                        #
# ============================================================================ #

# ======================= #ANCHOR - CREATE PURCHASE REQUEST ================= #

@ns.route("")
class PurchaseRequestListResource(Resource):

    @jwt_required()
    @ns.expect(purchase_request_create_model)
    @measure_execution_time
    def post(self):
        """Create Purchase Request"""

        body = request.get_json()
        body["id_pegawai"] = int(get_jwt_identity())
        data = create_purchase_request_service(body)

        return success(
            data=data,
            message="Purchase request berhasil dibuat."
        )
    
    
    @jwt_required()
    @ns.expect(purchase_request_filter_parser)
    @measure_execution_time
    def get(self):
        """List Purchase Request"""

        filters = purchase_request_filter_parser.parse_args()
        claims = get_jwt()
        account_type = claims.get("account_type")
        id_user = int(get_jwt_identity())

        data = get_purchase_request_list_service(
            id_user=id_user,
            account_type=account_type,
            filters=filters
        )

        return success(
            data=data,
            message="List purchase request"
        )

# ================ #!SECTION - PURCHASE REQUEST OPERATION =================== #



# ============================================================================ #
#                    #SECTION - DETAIL PURCHASE REQUEST                       #
# ============================================================================ #

# ======================= #ANCHOR - DETAIL REQUEST =========================== #

@ns.route("/<int:id_request>")
class PurchaseRequestDetailResource(Resource):

    @jwt_required()
    @measure_execution_time
    def get(self, id_request):
        """Detail Purchase Request"""

        claims = get_jwt()

        data = get_purchase_request_detail_service(
            id_request=id_request,
            account_type=claims.get("account_type"),
            id_pegawai=int(claims.get("sub"))
            if claims.get("account_type") == "pegawai"
            else None
        )

        return success(
            data=data,
            message="Detail purchase request"
        )
    
    
    @jwt_required()
    @ns.expect(purchase_request_update_model)
    @measure_execution_time
    def put(self, id_request):
        """Update Purchase Request"""

        body = request.get_json()

        if not body:
            raise ValidationError("Data pengajuan wajib diisi.")

        id_pegawai = int(get_jwt_identity())

        update_purchase_request_service(
            id_request=id_request,
            id_pegawai=id_pegawai,
            body=body
        )

        return success(
            message="Pengajuan berhasil diperbarui."
        )


    @jwt_required()
    @measure_execution_time
    def delete(self, id_request):
        """Soft Delete Purchase Request"""

        id_pegawai = int(get_jwt_identity())
        claims = get_jwt()

        is_admin = claims.get("account_type") == "admin"

        delete_purchase_request_service(
            id_request=id_request,
            id_pegawai=id_pegawai,
            is_admin=is_admin
        )

        return success(
            message="Pengajuan berhasil dihapus."
        )

# ==================== #!SECTION - DETAIL PURCHASE REQUEST =================== #



# ============================================================================ #
#                            #SECTION - DATA HISTORY                           #
# ============================================================================ #


@ns.route("/history")
class PurchaseRequestHistoryResource(Resource):

    @jwt_required()
    @ns.expect(purchase_request_history_parser)
    @measure_execution_time
    def get(self):
        """History Purchase Request"""

        filters = request.args.to_dict()
        claims = get_jwt()
        account_type = claims.get("account_type")
        id_user = int(get_jwt_identity())

        data = get_purchase_request_data_history_service(
            id_user=id_user,
            account_type=account_type,
            filters=filters
        )

        return success(
            data=data,
            message="History purchase request berhasil diambil."
        )

# ========================== #!SECTION - DATA HISTORY ======================== #



# ============================================================================ #
#                            #SECTION - STATUS UPDATE                          #
# ============================================================================ #

@ns.route("/<int:id_request>/review")
class PurchaseRequestReviewResource(Resource):

    @jwt_required()
    @ns.expect(purchase_request_review_model)
    @measure_execution_time
    def post(self, id_request):
        """Review Purchase Request"""

        claims = get_jwt()

        if claims.get("account_type") != "admin":
            raise ValidationError("Hanya admin yang dapat melakukan review.")

        body = request.get_json(silent=True) or {}

        display_name = claims.get("display_name")

        if not display_name:
            raise ValidationError("Identitas admin tidak ditemukan.")

        review_purchase_request_service(
            id_request=id_request,
            nama_pegawai=display_name,
            note=body.get("note")
        )

        return success(
            message="Pengajuan berhasil direview."
        )


@ns.route("/<int:id_request>/approve")
class PurchaseRequestApproveResource(Resource):

    @jwt_required()
    @ns.expect(purchase_request_approve_model)
    @measure_execution_time
    def post(self, id_request):
        """Approve Purchase Request"""

        claims = get_jwt()

        if claims.get("account_type") != "admin":
            raise ValidationError("Hanya admin yang dapat melakukan approval.")

        body = request.get_json(silent=True) or {}

        nama_pegawai = claims.get("display_name")

        if not nama_pegawai:
            raise ValidationError("Identitas admin tidak ditemukan.")

        approve_purchase_request_service(
            id_request=id_request,
            nama_pegawai=nama_pegawai,
            note=body.get("note")
        )

        return success(
            message="Pengajuan berhasil disetujui."
        )


@ns.route("/<int:id_request>/reject")
class PurchaseRequestRejectResource(Resource):

    @jwt_required()
    @ns.expect(purchase_request_reject_model)
    @measure_execution_time
    def post(self, id_request):
        """Reject Purchase Request"""

        claims = get_jwt()

        if claims.get("account_type") != "admin":
            raise ValidationError("Hanya admin yang dapat melakukan reject.")

        body = request.get_json(silent=True) or {}

        if not body.get("note") or not body["note"].strip():
            raise ValidationError("Alasan reject wajib diisi.")

        nama_pegawai = claims.get("display_name")

        if not nama_pegawai:
            raise ValidationError("Identitas admin tidak ditemukan.")

        reject_purchase_request_service(
            id_request=id_request,
            nama_pegawai=nama_pegawai,
            note=body["note"].strip()
        )

        return success(
            message="Pengajuan berhasil ditolak."
        )


@ns.route("/<int:id_request>/paid")
class PurchaseRequestPaidResource(Resource):

    @jwt_required()
    @ns.expect(purchase_request_paid_model)
    @measure_execution_time
    def post(self, id_request):
        """Mark Purchase Request as Paid"""

        claims = get_jwt()

        if claims.get("account_type") != "admin":
            raise ValidationError("Hanya admin yang dapat menandai pengajuan sebagai paid.")

        body = request.get_json(silent=True) or {}

        nama_pegawai = claims.get("display_name")

        if not nama_pegawai:
            raise ValidationError("Identitas admin tidak ditemukan.")

        mark_purchase_request_paid_service(
            id_request=id_request,
            nama_pegawai=nama_pegawai,
            note=body.get("note")
        )

        return success(
            message="Pengajuan berhasil ditandai sebagai paid."
        )

# ========================= #!SECTION - STATUS UPDATE ======================== #



# ======================= #ANCHOR - REQUEST HISTORY =========================== #

@ns.route("/<int:id_request>/history")
class PurchaseRequestHistoryResource(Resource):

    @jwt_required()
    @measure_execution_time
    def get(self, id_request):
        """Get Purchase Request History"""

        claims = get_jwt()

        is_admin = claims.get("account_type") == "admin"
        id_pegawai = int(get_jwt_identity()) if not is_admin else None

        data = get_purchase_request_history_service(
            id_request=id_request,
            id_pegawai=id_pegawai,
            is_admin=is_admin
        )

        return success(
            data=data,
            message="History pengajuan berhasil diambil."
        )

# ================== #!SECTION - REQUEST HISTORY ============================= #



# ============================================================================ #
#                     #SECTION - USER DASHBOARD                                #
# ============================================================================ #

# ======================= #ANCHOR - MY SUMMARY =============================== #

@ns.route("/my-summary")
class PurchaseRequestMySummaryResource(Resource):

    @jwt_required()
    @measure_execution_time
    def get(self):
        """Dashboard Purchase Request User"""

        id_pegawai = int(get_jwt_identity())

        data = get_my_purchase_request_summary_service(
            id_pegawai=id_pegawai
        )

        return success(
            data=data,
            message="Dashboard purchase request berhasil diambil."
        )

# ==================== #!SECTION - USER DASHBOARD ============================ #



# ============================================================================ #
#                       #SECTION - EXPORT PURCHASE REQUEST                     #
# ============================================================================ #

# ===================== #ANCHOR - DOWNLOAD PURCHASE REQUEST =================== #

@ns.route("/<int:id_request>/pdf")
class PurchaseRequestPdfResource(Resource):

    @jwt_required()
    @measure_execution_time
    def get(self, id_request):
        """Download Purchase Request PDF"""

        claims = get_jwt()

        account_type = claims.get("account_type")

        # =================================================
        # PEGAWAI
        # =================================================

        id_pegawai = None

        if account_type == "pegawai":
            id_pegawai = int(
                get_jwt_identity()
            )

        # =================================================
        # GENERATE PDF
        # =================================================

        result = generate_purchase_request_pdf_service(
            id_request=id_request,
            id_pegawai=id_pegawai
        )

        # =================================================
        # DOWNLOAD
        # =================================================

        return send_file(
            result["pdf"],
            mimetype="application/pdf",
            as_attachment=True,
            download_name=result["filename"]
        )

# ================= #!SECTION - DOWNLOAD PURCHASE REQUEST ====================== #