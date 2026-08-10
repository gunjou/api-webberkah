# api/cashbook/account/__init__.py

from flask_restx import Namespace

ns = Namespace(
    "cashbook/accounts",
    description="Cashbook Account Management"
)

from . import endpoint