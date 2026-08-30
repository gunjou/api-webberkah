from flask_restx import Namespace

ns = Namespace(
    "work-item/master",
    description="Work Item Master Data"
)

from . import endpoint