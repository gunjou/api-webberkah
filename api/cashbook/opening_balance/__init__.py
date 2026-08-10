from flask_restx import Namespace

ns = Namespace(
    "cashbook/opening-balance",
    description="Cashbook Opening Balance Management"
)

from . import endpoint