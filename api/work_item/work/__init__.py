from flask_restx import Namespace

ns = Namespace(
    "work-item/work",
    description="Work Item"
)

from . import endpoint