# api/cashbook/category/__init__.py
from flask_restx import Namespace

ns = Namespace(
    "cashbook/categories",
    description="Cashbook Category Management"
)

from . import endpoint