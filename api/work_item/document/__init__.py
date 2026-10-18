from flask_restx import Namespace

ns = Namespace(
    "work-item/legal-document",
    description="Legal Document Work Item"
)

from . import endpoint