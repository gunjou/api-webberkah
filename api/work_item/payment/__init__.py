from flask_restx import Namespace

ns = Namespace(
    "work-item/payment",
    description="Work Item Payment"
)

from . import endpoint