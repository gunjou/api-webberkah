from flask_restx import Resource

from api.shared.response import success
from api.utils.decorator import measure_execution_time, role_required
from flask_jwt_extended import jwt_required

from . import ns
from .service import *


# ======================= #ANCHOR - FILTER PARSER ============================ #

dashboard_activity_parser = ns.parser()

dashboard_activity_parser.add_argument(
    "limit",
    type=int,
    required=False,
    default=10,
    location="args",
    help="Jumlah aktivitas yang ditampilkan. Maksimal 50."
)


# ============================================================================ #
#                       #SECTION - DASHBOARD SUMMARY                          #
# ============================================================================ #

@ns.route("/admin/summary")
class DashboardSummaryResource(Resource):

    @jwt_required()
    @measure_execution_time
    def get(self):
        """Get Work Item Dashboard Summary"""

        data = get_dashboard_summary_service()

        return success(
            data=data,
            message="Data dashboard berhasil diambil"
        )


# ============================================================================ #
#                       #SECTION - DASHBOARD ACTIVITY                         #
# ============================================================================ #

@ns.route("/admin/activity")
class DashboardActivityResource(Resource):

    @jwt_required()
    @ns.expect(dashboard_activity_parser)
    @measure_execution_time
    def get(self):
        """Get Work Item Dashboard Activity"""

        filters = dashboard_activity_parser.parse_args()

        limit = filters.get("limit")

        data = get_dashboard_activity_service(
            limit=limit
        )

        return success(
            data=data,
            message="Aktivitas dashboard berhasil diambil"
        )


# ============================================================================ #
#                    #SECTION - DASHBOARD WORK SUMMARY                         #
# ============================================================================ #

@ns.route("/summary")
class DashboardWorkSummaryResource(Resource):

    @jwt_required()
    @role_required(['dashboard', 'admin'])
    @measure_execution_time
    def get(self):
        """Get Dashboard Work Summary"""

        data = get_dashboard_work_summary_service()

        return success(
            data=data,
            message="Data monitoring pekerjaan berhasil diambil"
        )


# ============================================================================ #
#                    #SECTION - DASHBOARD WARNINGS                             #
# ============================================================================ #

@ns.route("/warnings")
class DashboardWarningsResource(Resource):

    @jwt_required()
    @role_required(['dashboard', 'admin'])
    @measure_execution_time
    def get(self):
        """Get Dashboard Work and Invoice Warnings"""

        data = get_dashboard_warnings_service()

        return success(
            data=data,
            message="Data warning pekerjaan dan invoice berhasil diambil"
        )


# ============================================================================ #
#                    #SECTION - DASHBOARD FINANCIAL SUMMARY                    #
# ============================================================================ #

@ns.route("/financial-summary")
class DashboardFinancialSummaryResource(Resource):

    @jwt_required()
    @role_required(['dashboard', 'admin'])
    @measure_execution_time
    def get(self):
        """Get Dashboard Financial Summary"""

        data = get_dashboard_financial_summary_service()

        return success(
            data=data,
            message="Data monitoring keuangan berhasil diambil"
        )
