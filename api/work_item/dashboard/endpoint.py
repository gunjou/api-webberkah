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


# ============================================================================ #
# ============================================================================ #
#                         #SECTION - DASHBOARD V2                              #
#         Fokus monitoring pekerjaan, reminder, dan potensi invoice.           #
#         Endpoint V1 di atas dibiarkan sebagai backup.                        #
# ============================================================================ #
# ============================================================================ #

from .service_v2 import (
    REMINDER_LEVELS,
    REMINDER_TYPES,
    get_v2_monitoring_service,
    get_v2_reminders_service,
    get_v2_invoice_potential_service,
)


# ======================= #ANCHOR - V2 FILTER PARSER ========================= #

v2_work_type_parser = ns.parser()

v2_work_type_parser.add_argument(
    "work_type",
    type=str,
    required=False,
    choices=["TENDER", "MAINTENANCE"],
    location="args",
    help="Filter jenis pekerjaan: TENDER / MAINTENANCE"
)

v2_reminder_parser = v2_work_type_parser.copy()

v2_reminder_parser.add_argument(
    "level",
    type=str,
    required=False,
    choices=REMINDER_LEVELS,
    location="args",
    help="Filter tingkat reminder"
)

v2_reminder_parser.add_argument(
    "type",
    type=str,
    required=False,
    choices=REMINDER_TYPES,
    location="args",
    help="Filter jenis reminder: WORK / INVOICE"
)


# ======================= #ANCHOR - V2 MONITORING ============================ #

@ns.route("/v2/monitoring")
class DashboardV2MonitoringResource(Resource):

    @jwt_required()
    @role_required(['dashboard', 'admin'])
    @ns.expect(v2_work_type_parser)
    @measure_execution_time
    def get(self):
        """[V2] Posisi pekerjaan per stage beserta reminder dan status tertinggal"""

        filters = v2_work_type_parser.parse_args()

        data = get_v2_monitoring_service(
            work_type=filters.get("work_type")
        )

        return success(
            data=data,
            message="Data monitoring pekerjaan berhasil diambil"
        )


# ======================= #ANCHOR - V2 REMINDERS ============================= #

@ns.route("/v2/reminders")
class DashboardV2RemindersResource(Resource):

    @jwt_required()
    @role_required(['dashboard', 'admin'])
    @ns.expect(v2_reminder_parser)
    @measure_execution_time
    def get(self):
        """[V2] Reminder pekerjaan & invoice berdasarkan jarak ke due date (H-30 s.d. OVERDUE)"""

        filters = v2_reminder_parser.parse_args()

        data = get_v2_reminders_service(
            level=filters.get("level"),
            reminder_type=filters.get("type"),
            work_type=filters.get("work_type"),
        )

        return success(
            data=data,
            message="Data reminder berhasil diambil"
        )


# ======================= #ANCHOR - V2 INVOICE POTENTIAL ===================== #

@ns.route("/v2/invoice-potential")
class DashboardV2InvoicePotentialResource(Resource):

    @jwt_required()
    @role_required(['dashboard', 'admin'])
    @ns.expect(v2_work_type_parser)
    @measure_execution_time
    def get(self):
        """[V2] Potensi uang masuk dari invoice yang belum lunas (termasuk PPN)"""

        filters = v2_work_type_parser.parse_args()

        data = get_v2_invoice_potential_service(
            work_type=filters.get("work_type")
        )

        return success(
            data=data,
            message="Data potensi invoice berhasil diambil"
        )
