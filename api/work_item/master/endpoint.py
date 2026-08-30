from flask import request
from flask_jwt_extended import jwt_required, get_jwt
from flask_restx import Resource, fields

from api.shared.response import success
from api.shared.exceptions import ValidationError
from api.utils.decorator import measure_execution_time

from . import ns
from .service import *


# ======================= #ANCHOR - SWAGGER MODEL ============================ #

client_model = ns.model(
    "WorkItemClient", {
        "code": fields.String(required=True, description="Client Code"),
        "name": fields.String(required=True, description="Client Name"),
        "address": fields.String(required=False, description="Client Address"),
        "phone": fields.String(required=False, description="Client Phone"),
        "email": fields.String(required=False, description="Client Email")
    }
)

client_update_model = ns.model(
    "WorkItemClientUpdate", {
        "code": fields.String(required=True, description="Client Code"),
        "name": fields.String(required=True, description="Client Name"),
        "address": fields.String(required=False, description="Client Address"),
        "phone": fields.String(required=False, description="Client Phone"),
        "email": fields.String(required=False, description="Client Email"),
        "is_active": fields.Integer(required=False, description="Active Status: 1/0")
    }
)

client_pic_model = ns.model(
    "WorkItemClientPIC", {
        "name": fields.String(required=True, description="PIC Name"),
        "position": fields.String(required=False, description="PIC Position"),
        "phone": fields.String(required=False, description="PIC Phone"),
        "email": fields.String(required=False, description="PIC Email")
    }
)

client_pic_update_model = ns.model(
    "WorkItemClientPICUpdate", {
        "name": fields.String(required=True, description="PIC Name"),
        "position": fields.String(required=False, description="PIC Position"),
        "phone": fields.String(required=False, description="PIC Phone"),
        "email": fields.String(required=False, description="PIC Email"),
        "is_active": fields.Integer(required=False, description="Active Status: 1/0")
    }
)


# ======================= #ANCHOR - FILTER PARSER ============================ #

client_filter_parser = ns.parser()
client_filter_parser.add_argument("search", type=str, required=False)
client_filter_parser.add_argument("is_active", type=int, required=False)


# ============================================================================ #
#                         #SECTION - CLIENT                                   #
# ============================================================================ #

@ns.route("/clients")
class ClientListResource(Resource):

    @jwt_required()
    @ns.expect(client_filter_parser)
    @measure_execution_time
    def get(self):
        """List Client"""

        filters = request.args.to_dict()
        data = get_client_list_service(filters)

        return success(
            data=data,
            message="List client"
        )

    @jwt_required()
    @ns.expect(client_model)
    @measure_execution_time
    def post(self):
        """Create Client"""

        body = request.get_json() or {}
        body["created_by"] = get_jwt().get("display_name")

        id_client = create_client_service(body)

        return success(
            data={"id_client": id_client},
            message="Client berhasil ditambahkan."
        )


@ns.route("/clients/options")
class ClientOptionsResource(Resource):

    @jwt_required()
    @measure_execution_time
    def get(self):
        """List Client Options"""

        data = get_client_options_service()

        return success(
            data=data,
            message="List client options"
        )


@ns.route("/clients/<int:id_client>")
class ClientResource(Resource):

    @jwt_required()
    @measure_execution_time
    def get(self, id_client):
        """Detail Client"""

        data = get_client_detail_service(id_client)

        return success(
            data=data,
            message="Detail client"
        )

    @jwt_required()
    @ns.expect(client_update_model)
    @measure_execution_time
    def put(self, id_client):
        """Update Client"""

        body = request.get_json() or {}
        body["updated_by"] = get_jwt().get("display_name")

        update_client_service(
            id_client=id_client,
            body=body
        )

        return success(
            message="Client berhasil diperbarui."
        )
    
    @jwt_required()
    @measure_execution_time
    def delete(self, id_client):
        """Nonaktifkan Client"""

        updated_by = get_jwt().get("display_name")

        delete_client_service(
            id_client=id_client,
            updated_by=updated_by
        )

        return success(
            message="Client berhasil dinonaktifkan."
        )


# ============================================================================ #
#                         #SECTION - CLIENT PIC                               #
# ============================================================================ #

@ns.route("/client-pics")
class ClientPICAllResource(Resource):

    @jwt_required()
    @measure_execution_time
    def get(self):
        """List All Client PIC"""

        data = get_all_client_pic_service()

        return success(
            data=data,
            message="List all client PIC"
        )


@ns.route("/clients/<int:id_client>/pics")
class ClientPICListResource(Resource):

    @jwt_required()
    @measure_execution_time
    def get(self, id_client):
        """List Client PIC"""

        data = get_client_pic_list_service(id_client)

        return success(
            data=data,
            message="List client PIC"
        )

    @jwt_required()
    @ns.expect(client_pic_model)
    @measure_execution_time
    def post(self, id_client):
        """Create Client PIC"""

        body = request.get_json() or {}
        body["id_client"] = id_client
        body["created_by"] = get_jwt().get("display_name")

        id_client_pic = create_client_pic_service(body)

        return success(
            data={"id_client_pic": id_client_pic},
            message="Client PIC berhasil ditambahkan."
        )


@ns.route("/client-pics/<int:id_client_pic>")
class ClientPICResource(Resource):

    @jwt_required()
    @measure_execution_time
    def get(self, id_client_pic):
        """Detail Client PIC"""

        data = get_client_pic_detail_service(id_client_pic)

        return success(
            data=data,
            message="Detail client PIC"
        )

    @jwt_required()
    @ns.expect(client_pic_update_model)
    @measure_execution_time
    def put(self, id_client_pic):
        """Update Client PIC"""

        body = request.get_json() or {}
        body["updated_by"] = get_jwt().get("display_name")

        update_client_pic_service(
            id_client_pic=id_client_pic,
            body=body
        )

        return success(
            message="Client PIC berhasil diperbarui."
        )
    
    @jwt_required()
    @measure_execution_time
    def delete(self, id_client_pic):
        """Nonaktifkan Client PIC"""

        updated_by = get_jwt().get("display_name")

        delete_client_pic_service(
            id_client_pic=id_client_pic,
            updated_by=updated_by
        )

        return success(
            message="Client PIC berhasil dinonaktifkan."
        )