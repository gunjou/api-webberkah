from datetime import date, timedelta
from decimal import Decimal

from api.shared.exceptions import ValidationError
from .query_v2 import get_v2_work_monitoring, get_v2_unpaid_invoices


# ============================================================================ #
#                              #SECTION - CONSTANT                             #
# ============================================================================ #

STAGE_OPTIONS = [
    ("IDENTIFIED", "Identified"),
    ("QUOTATION", "Quotation"),
    ("CONTRACT", "Contract"),
    ("COMPLETED", "Completed"),
    ("BA", "BA"),
    ("INVOICE", "Invoice"),
    ("PAYMENT", "Payment"),
]

# Urutan dari paling mendesak
REMINDER_LEVELS = ["OVERDUE", "TODAY", "H-3", "H-7", "H-14", "H-30"]

REMINDER_TYPES = ["WORK", "INVOICE"]

# Stage yang reminder-nya diwakili oleh baris invoice
INVOICE_STAGES = ("INVOICE", "PAYMENT")

WORK_REMINDER_MESSAGE = {
    "IDENTIFIED": "Segera buat penawaran",
    "QUOTATION": "Penawaran akan/sudah kedaluwarsa",
    "CONTRACT": "Pekerjaan harus selesai sesuai kontrak",
    "COMPLETED": "Pekerjaan selesai, segera buat BA",
    "BA": "BA sudah terbit, segera buat invoice",
}


def _empty_level_count():
    return {level: 0 for level in REMINDER_LEVELS}


def _to_dict(row):
    return dict(row)


# ============================================================================ #
#                           #SECTION - MONITORING                              #
# ============================================================================ #

def get_v2_monitoring_service(work_type=None):

    rows = [_to_dict(r) for r in get_v2_work_monitoring()]

    if work_type:
        rows = [r for r in rows if r["work_type"] == work_type]

    stages = {
        code: {
            "stage": code,
            "label": label,
            "total": 0,
            "behind_schedule": 0,
            "reminder": _empty_level_count(),
            "items": [],
        }
        for code, label in STAGE_OPTIONS
    }

    summary = {
        "total_active": len(rows),
        "tender": 0,
        "maintenance": 0,
        "behind_schedule": 0,
        "overdue": 0,
        "need_attention": 0,  # OVERDUE s.d. H-30
    }

    for row in rows:
        stage = row["current_stage"]
        level = row["reminder_level"]

        if row["work_type"] == "TENDER":
            summary["tender"] += 1
        elif row["work_type"] == "MAINTENANCE":
            summary["maintenance"] += 1

        if row["is_behind_schedule"]:
            summary["behind_schedule"] += 1

        if level == "OVERDUE":
            summary["overdue"] += 1

        if level in REMINDER_LEVELS:
            summary["need_attention"] += 1

        if stage not in stages:
            stages[stage] = {
                "stage": stage,
                "label": stage.replace("_", " ").title(),
                "total": 0,
                "behind_schedule": 0,
                "reminder": _empty_level_count(),
                "items": [],
            }

        bucket = stages[stage]
        bucket["total"] += 1

        if row["is_behind_schedule"]:
            bucket["behind_schedule"] += 1

        if level in bucket["reminder"]:
            bucket["reminder"][level] += 1

        bucket["items"].append(row)

    return {
        "summary": summary,
        "stages": list(stages.values()),
    }


# ============================================================================ #
#                            #SECTION - REMINDERS                              #
# ============================================================================ #

def _build_work_reminder(row):
    return {
        "reminder_type": "WORK",
        "reminder_level": row["reminder_level"],
        "message": WORK_REMINDER_MESSAGE.get(row["current_stage"], "Perlu tindak lanjut"),
        "deadline_date": row["deadline_date"],
        "days_to_deadline": row["days_to_deadline"],
        "days_overdue": max(-row["days_to_deadline"], 0),
        "id_work_item": row["id_work_item"],
        "work_number": row["work_number"],
        "work_name": row["work_name"],
        "work_type": row["work_type"],
        "current_stage": row["current_stage"],
        "progress_percent": row["progress_percent"],
        "is_behind_schedule": row["is_behind_schedule"],
        "client_name": row["client_name"],
        "internal_pic_name": row["internal_pic_name"],
        "id_invoice": None,
        "invoice_number": None,
        "outstanding_amount": None,
    }


def _build_invoice_reminder(row):
    return {
        "reminder_type": "INVOICE",
        "reminder_level": row["reminder_level"],
        "message": (
            "Invoice sudah lewat jatuh tempo"
            if row["reminder_level"] == "OVERDUE"
            else "Invoice akan jatuh tempo"
        ),
        "deadline_date": row["due_date"],
        "days_to_deadline": row["days_to_deadline"],
        "days_overdue": max(-row["days_to_deadline"], 0),
        "id_work_item": row["id_work_item"],
        "work_number": row["work_number"],
        "work_name": row["work_name"],
        "work_type": row["work_type"],
        "current_stage": row["current_stage"],
        "progress_percent": None,
        "is_behind_schedule": None,
        "client_name": row["client_name"],
        "internal_pic_name": row["internal_pic_name"],
        "id_invoice": row["id_invoice"],
        "invoice_number": row["invoice_number"],
        "outstanding_amount": row["outstanding_amount"],
    }


def get_v2_reminders_service(level=None, reminder_type=None, work_type=None):

    if level and level not in REMINDER_LEVELS:
        raise ValidationError(
            f"Level tidak valid. Pilihan: {', '.join(REMINDER_LEVELS)}"
        )

    if reminder_type and reminder_type not in REMINDER_TYPES:
        raise ValidationError(
            f"Type tidak valid. Pilihan: {', '.join(REMINDER_TYPES)}"
        )

    reminders = []

    if reminder_type in (None, "WORK"):
        for row in get_v2_work_monitoring():
            if row["current_stage"] in INVOICE_STAGES:
                continue
            if row["reminder_level"] not in REMINDER_LEVELS:
                continue
            reminders.append(_build_work_reminder(row))

    if reminder_type in (None, "INVOICE"):
        for row in get_v2_unpaid_invoices():
            if row["reminder_level"] not in REMINDER_LEVELS:
                continue
            reminders.append(_build_invoice_reminder(row))

    if work_type:
        reminders = [r for r in reminders if r["work_type"] == work_type]

    # Hitung per level sebelum filter level, agar badge tetap lengkap
    level_count = _empty_level_count()
    for r in reminders:
        level_count[r["reminder_level"]] += 1

    if level:
        reminders = [r for r in reminders if r["reminder_level"] == level]

    reminders.sort(key=lambda r: (r["days_to_deadline"], r["work_number"] or ""))

    return {
        "total": len(reminders),
        "level_count": level_count,
        "items": reminders,
    }


# ============================================================================ #
#                         #SECTION - INVOICE POTENTIAL                         #
# ============================================================================ #

def get_v2_invoice_potential_service(work_type=None):

    rows = [_to_dict(r) for r in get_v2_unpaid_invoices()]

    if work_type:
        rows = [r for r in rows if r["work_type"] == work_type]

    today = date.today()
    end_of_week = today + timedelta(days=6 - today.weekday())
    next_month = (today.replace(day=28) + timedelta(days=4)).replace(day=1)
    end_of_month = next_month - timedelta(days=1)

    buckets = {
        key: {"key": key, "label": label, "total_amount": Decimal("0"), "total_invoices": 0}
        for key, label in [
            ("OVERDUE", "Lewat jatuh tempo"),
            ("THIS_WEEK", "Jatuh tempo minggu ini"),
            ("THIS_MONTH", "Jatuh tempo bulan ini"),
            ("LATER", "Jatuh tempo setelah bulan ini"),
            ("NO_DUE_DATE", "Tanpa jatuh tempo"),
        ]
    }

    total = Decimal("0")

    for row in rows:
        amount = Decimal(str(row["outstanding_amount"] or 0))
        due = row["due_date"]

        if due is None:
            key = "NO_DUE_DATE"
        elif due < today:
            key = "OVERDUE"
        elif due <= end_of_week:
            key = "THIS_WEEK"
        elif due <= end_of_month:
            key = "THIS_MONTH"
        else:
            key = "LATER"

        row["due_bucket"] = key
        buckets[key]["total_amount"] += amount
        buckets[key]["total_invoices"] += 1
        total += amount

    return {
        "total_potential": total,
        "total_invoices": len(rows),
        "buckets": list(buckets.values()),
        "items": [
            {
                "id_invoice": r["id_invoice"],
                "invoice_number": r["invoice_number"],
                "invoice_date": r["invoice_date"],
                "due_date": r["due_date"],
                "days_to_deadline": r["days_to_deadline"],
                "reminder_level": r["reminder_level"],
                "due_bucket": r["due_bucket"],
                "outstanding_amount": r["outstanding_amount"],
                "id_work_item": r["id_work_item"],
                "work_number": r["work_number"],
                "work_name": r["work_name"],
                "work_type": r["work_type"],
                "current_stage": r["current_stage"],
                "client_name": r["client_name"],
            }
            for r in rows
        ],
    }
