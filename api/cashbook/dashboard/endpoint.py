from flask import request
from flask_restx import Resource
from flask_jwt_extended import jwt_required

from api.shared.response import success
from api.utils.decorator import measure_execution_time
from api.security.cashbook import cashbook_role_required

from . import ns
from .service import *


dashboard_parser = ns.parser()
dashboard_parser.add_argument("period", type=str, choices=["today", "week", "month", "year"])
dashboard_parser.add_argument("id_account", type=int, required=False)


@ns.route("/summary")
class DashboardSummaryResource(Resource):

    @jwt_required()
    @cashbook_role_required()
    @ns.expect(dashboard_parser)
    @measure_execution_time
    def get(self):

        filters = request.args.to_dict()

        return success(
            data=get_dashboard_summary_service(filters),
            message="Dashboard summary"
        )


@ns.route("/cashflow")
class DashboardCashflowResource(Resource):

    @jwt_required()
    @cashbook_role_required()
    @ns.expect(dashboard_parser)
    @measure_execution_time
    def get(self):

        filters = request.args.to_dict()
        print(filters)
        # if filters == []:
        #     filters["period"] = 'week'

        return success(
            data=get_dashboard_cashflow_service(filters),
            message="Dashboard cashflow"
        )


@ns.route("/recent-transactions")
class DashboardRecentTransactionResource(Resource):

    @jwt_required()
    @cashbook_role_required()
    @ns.expect(dashboard_parser)
    @measure_execution_time
    def get(self):

        filters = request.args.to_dict()

        return success(
            data=get_dashboard_recent_transaction_service(filters),
            message="Recent transactions"
        )


@ns.route("/expense-category")
class DashboardExpenseCategoryResource(Resource):

    @jwt_required()
    @cashbook_role_required()
    @ns.expect(dashboard_parser)
    @measure_execution_time
    def get(self):

        filters = request.args.to_dict()

        return success(
            data=get_dashboard_expense_category_service(filters),
            message="Expense category"
        )


@ns.route("/expense-account")
class DashboardExpenseAccountResource(Resource):

    @jwt_required()
    @cashbook_role_required()
    @ns.expect(dashboard_parser)
    @measure_execution_time
    def get(self):

        filters = request.args.to_dict()

        return success(
            data=get_dashboard_expense_account_service(filters),
            message="Expense account"
        )