from datetime import datetime, timedelta
import calendar

from api.shared.exceptions import ValidationError

from .query import *


# ============================================================================ #
#                             #SECTION - PRIVATE HELPER                        #
# ============================================================================ #

def _get_period_range(period: str = "week"):

    today = datetime.today().date()
    period = (period or "week").lower()

    if period == "today":

        date_from = today
        date_to = today

    elif period == "week":

        date_from = today - timedelta(days=today.weekday())
        date_to = date_from + timedelta(days=6)

    elif period == "month":

        date_from = today.replace(day=1)
        date_to = today.replace(
            day=calendar.monthrange(today.year, today.month)[1]
        )

    elif period == "year":

        date_from = today.replace(month=1, day=1)
        date_to = today.replace(month=12, day=31)

    else:

        raise ValidationError(
            "Period harus bernilai today, week, month atau year."
        )

    return date_from, date_to


def get_dashboard_summary_service(filters: dict):

    date_from, date_to = _get_period_range(filters.get("period"))

    filters.update({
        "date_from": date_from,
        "date_to": date_to
    })

    summary = get_dashboard_summary(filters)
    balance = get_current_balance(filters.get("id_account"))

    return {
        "current_balance": balance,
        "total_income": summary["total_income"],
        "total_expense": summary["total_expense"],
        "net_cashflow": summary["net_cashflow"]
    }


def get_dashboard_cashflow_service(filters: dict):
    today = datetime.today().date()
    period = (filters.get("period") or "week").lower()
    period = "week" if period == "today" else period

    date_from, date_to = _get_period_range(period)

    filters.update({
        "period": period,
        "date_from": date_from,
        "date_to": date_to,
    })

    rows = get_dashboard_cashflow(filters)
    mapping = {row["label"]: row for row in rows}
    result = []

    if period == "week":
        labels = [
            "Senin", "Selasa", "Rabu", "Kamis",
            "Jum'at", "Sabtu", "Minggu"
        ]

        for i in range(7):
            date = date_from + timedelta(days=i)
            row = mapping.get(i + 1, {})

            result.append({
                "label": labels[i],
                "date": date.isoformat(),
                "income": row.get("income", 0),
                "expense": row.get("expense", 0),
            })

    elif period == "month":
        last_day = calendar.monthrange(today.year, today.month)[1]

        for day in range(1, last_day + 1):
            date = date_from.replace(day=day)
            row = mapping.get(day, {})

            result.append({
                "label": f"{day:02}",
                "date": date.isoformat(),
                "income": row.get("income", 0),
                "expense": row.get("expense", 0),
            })

    else:
        months = [
            "Januari", "Februari", "Maret", "April",
            "Mei", "Juni", "Juli", "Agustus",
            "September", "Oktober", "November", "Desember",
        ]

        for month in range(1, 13):
            date = date_from.replace(month=month, day=1)
            row = mapping.get(month, {})

            result.append({
                "label": months[month - 1],
                "date": date.isoformat(),
                "income": row.get("income", 0),
                "expense": row.get("expense", 0),
            })

    return result


def get_dashboard_recent_transaction_service(filters: dict):

    date_from, date_to = _get_period_range(filters.get("period", "week"))

    query_filters = {
        "id_account": filters.get("id_account"),
        "date_from": date_from,
        "date_to": date_to
    }

    return get_dashboard_recent_transactions(query_filters)


def get_dashboard_expense_category_service(filters: dict):

    date_from, date_to = _get_period_range(filters.get("period", "week"))

    query_filters = {
        "id_account": filters.get("id_account"),
        "date_from": date_from,
        "date_to": date_to
    }

    return get_dashboard_expense_category(query_filters)


def get_dashboard_expense_account_service(filters: dict):

    date_from, date_to = _get_period_range(filters.get("period", "week"))
    
    query_filters = {
        "date_from": date_from,
        "date_to": date_to
    }

    return get_dashboard_expense_account(query_filters)