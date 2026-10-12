from flask_restx import Namespace

ns = Namespace(
    "work-item/dashboard",
    description="Dashboard Work Item"
)

from . import endpoint