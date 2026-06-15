from flask_jwt_extended import jwt_required
from flask_restx import Namespace, Resource

from api.shared.response import success
from api.utils.decorator import measure_execution_time
from api.rcc.eis.query import *


eis_ns = Namespace("eis", description="Executive Information System")


@eis_ns.route("/summary")
class EISSummaryResource(Resource):

    @jwt_required()
    @measure_execution_time
    def get(self):
        """Executive Summary"""

        data = get_eis_summary()

        return success(
            data=data,
            message="Executive summary"
        )


@eis_ns.route("/critical-invoices")
class CriticalInvoiceResource(Resource):

    @jwt_required()
    @measure_execution_time
    def get(self):
        """Critical Invoice"""

        data = get_critical_invoices()

        return success(
            data=data,
            message="Critical invoices"
        )


@eis_ns.route("/outstanding-clients")
class OutstandingClientResource(Resource):

    @jwt_required()
    @measure_execution_time
    def get(self):
        """Outstanding Clients"""

        data = get_outstanding_clients()

        return success(
            data=data,
            message="Outstanding clients"
        )


@eis_ns.route("/aging-analysis")
class AgingAnalysisResource(Resource):

    @jwt_required()
    @measure_execution_time
    def get(self):
        """Aging Analysis"""

        data = get_aging_analysis()

        return success(
            data=data,
            message="Aging analysis"
        )


@eis_ns.route("/invoice-trend")
class InvoiceTrendResource(Resource):

    @jwt_required()
    @measure_execution_time
    def get(self):
        """Invoice Trend"""

        data = get_invoice_trend()

        return success(
            data=data,
            message="Invoice trend"
        )
