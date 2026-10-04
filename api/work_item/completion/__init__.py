from flask_restx import Namespace

ns = Namespace(
    "work-item/completion",
    description="Work Item Completion / BA"
)

from . import endpoint