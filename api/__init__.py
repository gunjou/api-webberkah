from flask import Flask
from flask_cors import CORS
from flask_restx import Api

from api.sample import sample_ns

app = Flask(__name__)
CORS(app)


# ==============================
# SWAGGER AUTH CONFIG
# ==============================
authorizations = {
    "Bearer Auth": {
        "type": "apiKey",
        "in": "header",
        "name": "Authorization",
        "description": "Gunakan format: **Bearer &lt;JWT&gt;**"
    }
}

# ==============================
# FLASK RESTX API
# ==============================
api = Api(
    app,
    version="2.0",
    title="Webberkah API",
    description="HRIS Backend Webberkah v2",
    doc="/docs",
    prefix="/",
    authorizations=authorizations,
    security="Bearer Auth"
)

# ==============================
# REGISTER NAMESPACES
# ==============================
api.add_namespace(sample_ns, path="/sample")