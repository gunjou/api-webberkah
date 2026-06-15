from flask_jwt_extended import jwt_required
from flask_restx import Namespace, Resource

from api.shared.response import success
from api.utils.decorator import measure_execution_time
from api.rcc.dashboard.query import *


rcc_dashboard_ns = Namespace("rcc-dashboard", description="RCC Dashboard")


@rcc_dashboard_ns.route("/summary")
class DashboardSummaryResource(
    Resource
):

    @jwt_required()
    @measure_execution_time
    def get(self):
        """Summary Dashboard"""

        data = get_dashboard_summary()

        return success(
            data=data,
            message="Summary dashboard"
        )


@rcc_dashboard_ns.route(
    "/invoice-monitoring"
)
class InvoiceMonitoringResource(
    Resource
):

    @jwt_required()
    @measure_execution_time
    def get(self):
        """Invoice Monitoring"""

        data = get_invoice_monitoring()

        return success(
            data=data,
            message="Invoice monitoring"
        )


@rcc_dashboard_ns.route(
    "/aging-invoice"
)
class AgingInvoiceResource(
    Resource
):

    @jwt_required()
    @measure_execution_time
    def get(self):
        """Aging Invoice"""

        data = get_aging_invoice()

        return success(
            data=data,
            message="Aging invoice"
        )


@rcc_dashboard_ns.route(
    "/top-outstanding-client"
)
class OutstandingClientResource(
    Resource
):

    @jwt_required()
    @measure_execution_time
    def get(self):
        """Top Outstanding Client"""

        data = get_top_outstanding_client()

        return success(
            data=data,
            message="Top outstanding client"
        )
