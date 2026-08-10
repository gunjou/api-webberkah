# api/cashbook/category/endpoint.py
from flask import request
from flask_jwt_extended import jwt_required

from flask_restx import Resource, fields

from api.shared.response import success
from api.shared.exceptions import ValidationError, NotFoundError

from api.utils.decorator import measure_execution_time
from api.security.cashbook import cashbook_role_required

from . import ns
from .query import *


# ============================================================================ #
#                            #ANCHOR - SWAGGER MODEL                           #
# ============================================================================ #
category_model = ns.model(
    "Category", {
        "name": fields.String(required=True, description="Nama Kategori"),
        "description": fields.String(required=False, description="Deskripsi Kategori")
    }
)


# ============================================================================ #
#                      #SECTION - BASIC OPERATION CATEGORY                     #
# ============================================================================ #

# ================ #ANCHOR - GET LIST CATEGORY & POST CATEGORY =============== #

@ns.route("")
class CategoryListResource(Resource):

    @jwt_required()
    @cashbook_role_required()
    @measure_execution_time
    def get(self):
        """List Category"""

        data = get_category_list()

        return success(
            data=data,
            message="List category"
        )

    @jwt_required()
    @cashbook_role_required()
    @measure_execution_time
    @ns.expect(category_model)
    def post(self):
        """Create Category"""

        body = request.json

        if not body.get("name"):
            raise ValidationError(
                "Nama kategori wajib diisi."
            )

        id_category = create_category(
            name=body["name"],
            description=body.get("description")
        )

        return success(
            data={
                "id_category": id_category
            },
            message="Kategori berhasil ditambahkan."
        )



# ============= #ANCHOR - DETAIL CATEGORY (GET | UPDATE | DELETE) ============ #

@ns.route("/<int:id_category>")
class CategoryResource(Resource):

    @jwt_required()
    @cashbook_role_required()
    @measure_execution_time
    def get(self, id_category):
        """Detail Category"""

        data = get_category_detail(
            id_category
        )

        if not data:
            raise NotFoundError(
                "Kategori tidak ditemukan."
            )

        return success(
            data=data,
            message="Detail category"
        )

    @jwt_required()
    @cashbook_role_required()
    @measure_execution_time
    @ns.expect(category_model)
    def put(self, id_category):
        """Update Category"""

        body = request.json

        if not body.get("name"):
            raise ValidationError(
                "Nama kategori wajib diisi."
            )

        affected = update_category(
            id_category=id_category,
            name=body["name"],
            description=body.get("description")
        )

        if affected == 0:
            raise NotFoundError(
                "Kategori tidak ditemukan."
            )

        return success(
            message="Kategori berhasil diperbarui."
        )

    @jwt_required()
    @cashbook_role_required()
    @measure_execution_time
    def delete(self, id_category):
        """Delete Category"""

        affected = delete_category(
            id_category
        )

        if affected == 0:
            raise NotFoundError(
                "Kategori tidak ditemukan."
            )

        return success(
            message="Kategori berhasil dihapus."
        )
# ==================== #!SECTION - BASIC OPERATION CATEGORY ================== #