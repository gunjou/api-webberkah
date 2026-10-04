from flask_restx import Namespace

ns = Namespace(
    "work-item/quotation",
    description="Work Item Quotation"
)

from . import endpoint