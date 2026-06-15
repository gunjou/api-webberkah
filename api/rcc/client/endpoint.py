from flask import request
from flask_restx import Namespace, Resource, fields
from flask_jwt_extended import jwt_required

from api.shared.response import success
from api.shared.exceptions import ValidationError, NotFoundError

from api.utils.decorator import measure_execution_time

from api.rcc.client.query import (
    get_client_list,
    get_client_by_id,
    create_client,
    update_client,
    delete_client
)

client_ns = Namespace(
    "clients",
    description="Client Management"
)

client_model = client_ns.model(
    "Client",
    {
        "nama_client": fields.String(required=True),
        "alamat": fields.String(),
        "telpon": fields.String(),
        "email": fields.String(),
        "keterangan": fields.String()
    }
)


@client_ns.route("")
class ClientListResource(Resource):

    @jwt_required()
    @measure_execution_time
    def get(self):
        """List Client"""
        data = get_client_list()

        return success(
            data=data,
            message="List client berhasil diambil"
        )

    @jwt_required()
    @client_ns.expect(client_model, validate=True)
    @measure_execution_time
    def post(self):
        """Tambah Client"""

        body = request.get_json()

        nama_client = body.get("nama_client")

        if not nama_client:
            raise ValidationError(
                "Nama client wajib diisi"
            )

        data = create_client(
            nama_client=nama_client,
            alamat=body.get("alamat"),
            telpon=body.get("telpon"),
            email=body.get("email"),
            keterangan=body.get("keterangan")
        )

        return success(
            data=data,
            message="Client berhasil ditambahkan"
        )


@client_ns.route("/<int:id_client>")
class ClientDetailResource(Resource):

    @jwt_required()
    @measure_execution_time
    def get(self, id_client):
        """Detail Client"""

        data = get_client_by_id(id_client)

        if not data:
            raise NotFoundError(
                "Client tidak ditemukan"
            )

        return success(
            data=data,
            message="Detail client"
        )

    @jwt_required()
    @client_ns.expect(client_model, validate=True)
    @measure_execution_time
    def put(self, id_client):
        """Update Client"""

        existing = get_client_by_id(id_client)

        if not existing:
            raise NotFoundError(
                "Client tidak ditemukan"
            )

        body = request.get_json()

        data = update_client(
            id_client=id_client,
            nama_client=body.get("nama_client"),
            alamat=body.get("alamat"),
            telpon=body.get("telpon"),
            email=body.get("email"),
            keterangan=body.get("keterangan")
        )

        return success(
            data=data,
            message="Client berhasil diperbarui"
        )

    @jwt_required()
    @measure_execution_time
    def delete(self, id_client):
        """Hapus Client"""

        existing = get_client_by_id(id_client)

        if not existing:
            raise NotFoundError(
                "Client tidak ditemukan"
            )

        delete_client(id_client)

        return success(
            message="Client berhasil dihapus"
        )