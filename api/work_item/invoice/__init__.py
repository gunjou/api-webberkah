from flask_restx import Namespace

ns = Namespace(
    "work-item/invoice",
    description="Work Item Invoice"
)

from . import endpoint