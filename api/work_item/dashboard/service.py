from decimal import Decimal

from api.shared.exceptions import ValidationError
from .query import *


# ============================================================================ #
#                        #SECTION - DASHBOARD SUMMARY                          #
# ============================================================================ #

def get_dashboard_summary_service():

    overview = get_dashboard_overview()

    work_type = get_dashboard_work_type()

    pipeline = get_dashboard_pipeline()

    financial = get_dashboard_financial()

    attention = get_dashboard_attention()

    return {
        "overview": overview,
        "work_type": work_type,
        "pipeline": pipeline,
        "financial": financial,
        "attention": attention
    }


# ============================================================================ #
#                        #SECTION - DASHBOARD ACTIVITY                         #
# ============================================================================ #

def get_dashboard_activity_service(limit=10):


    if limit is None:
        limit = 10

    if limit < 1:
        raise ValidationError(
            "Limit harus lebih besar atau sama dengan 1."
        )

    if limit > 50:
        raise ValidationError(
            "Limit maksimal 50."
        )


    return get_dashboard_activity(
        limit=limit
    )


def get_dashboard_work_summary_service():

    work_items = get_dashboard_work_summary()

    stage_options = [
        {"stage": "IDENTIFIED", "label": "Identified"},
        {"stage": "QUOTATION", "label": "Quotation"},
        {"stage": "CONTRACT", "label": "Contract"},
        {"stage": "COMPLETED", "label": "Completed"},
        {"stage": "BA", "label": "BA"},
        {"stage": "INVOICE", "label": "Invoice"},
        {"stage": "PAYMENT", "label": "Payment"}
    ]

    stages = {
        item["stage"]: {
            **item,
            "total": 0,
            "health": {
                "EXPIRED": 0,
                "DUE_SOON": 0,
                "ON_TRACK": 0
            },
            "items": []
        }
        for item in stage_options
    }

    total_tender = 0
    total_maintenance = 0

    for item in work_items:

        stage = item["current_stage"]
        work_type = item["work_type"]
        health = item["health_status"]

        if work_type == "TENDER":
            total_tender += 1

        elif work_type == "MAINTENANCE":
            total_maintenance += 1

        if stage not in stages:
            stages[stage] = {
                "stage": stage,
                "label": stage.replace("_", " ").title(),
                "total": 0,
                "health": {
                    "EXPIRED": 0,
                    "DUE_SOON": 0,
                    "ON_TRACK": 0
                },
                "items": []
            }

        stages[stage]["total"] += 1

        if health in stages[stage]["health"]:
            stages[stage]["health"][health] += 1

        stages[stage]["items"].append(item)

    return {
        "total_active": len(work_items),
        "tender": total_tender,
        "maintenance": total_maintenance,
        "stages": list(stages.values())
    }


# ============================================================================ #
#                    #SECTION - DASHBOARD WARNINGS                            #
# ============================================================================ #

def _group_warnings_by_health(items):

    health_options = [
        "EXPIRED",
        "DUE_SOON"
    ]

    grouped = {
        health: {
            "total": 0,
            "items": [],
        }
        for health in health_options
    }

    for item in items:
        health = item["health_status"]

        if health not in grouped:
            continue

        grouped[health]["items"].append(item)
        grouped[health]["total"] += 1

    return grouped


def get_dashboard_warnings_service():

    warnings = get_dashboard_warnings()

    return _group_warnings_by_health(warnings)


# ============================================================================ #
#                    #SECTION - DASHBOARD FINANCIAL SUMMARY                   #
# ============================================================================ #

def _sum_amount(items, field):

    return sum(
        (
            Decimal(str(item[field] or 0))
            for item in items
        ),
        Decimal("0"),
    )


def get_dashboard_financial_summary_service():

    contracts = get_dashboard_contract_financials()
    unbilled = get_dashboard_unbilled_financials()
    unpaid = get_dashboard_unpaid_invoice_financials()
    paid = get_dashboard_paid_invoice_financials()

    return {
        "contract": {
            "total_contract_value": _sum_amount(
                contracts,
                "total_contract_value",
            ),
            "total_contracts": len(contracts),
            "total_work_items": len({
                item["id_work_item"]
                for item in contracts
            }),
            "items": contracts,
        },

        "unbilled": {
            "total_value": _sum_amount(
                unbilled,
                "total_contract_value",
            ),
            "total_work_items": len(unbilled),
            "items": unbilled,
        },

        "unpaid": {
            "total_invoice_value": _sum_amount(
                unpaid,
                "total_invoice",
            ),
            "total_outstanding": _sum_amount(
                unpaid,
                "outstanding_amount",
            ),
            "total_invoices": len(unpaid),
            "items": unpaid,
        },

        "paid": {
            "total_invoice_value": _sum_amount(
                paid,
                "total_invoice",
            ),
            "total_received": _sum_amount(
                paid,
                "total_received",
            ),
            "total_invoices": len(paid),
            "items": paid,
        },
    }