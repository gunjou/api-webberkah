from flask_restx import Namespace

ns = Namespace(
    "work-item/contract",
    description="Work Item Contract"
)

from . import endpoint