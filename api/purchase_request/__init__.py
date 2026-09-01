# api/purchase_request/__init__.py
from flask_restx import Namespace

ns = Namespace(
    "purchase-requests",
    description="Purchase Request Management"
)

from . import endpoint