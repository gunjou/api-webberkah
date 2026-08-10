from flask_restx import Namespace

ns = Namespace(
    "cashbook/dashboard",
    description="Cashbook Dashboard"
)

from . import endpoint