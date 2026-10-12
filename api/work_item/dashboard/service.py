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

    # ============================== Validation =============================== #

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

    # ================================ Query ================================== #

    return get_dashboard_activity(
        limit=limit
    )