from flask_restx import Namespace

ns = Namespace(
    "cashbook/transactions",
    description="Cashbook Transaction Management"
)

from . import endpoint