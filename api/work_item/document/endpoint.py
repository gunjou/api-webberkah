
from flask_jwt_extended import jwt_required, get_jwt
from werkzeug.datastructures import FileStorage
from flask_restx import Resource
from flask import request

from api.shared.response import success
from api.utils.decorator import measure_execution_time

from . import ns
from .service import *


# ======================= #ANCHOR - FILTER PARSER ============================ #

document_filter_parser = ns.parser()

document_filter_parser.add_argument(
    "search",
    type=str,
    required=False,
    location="args",
    help="Pencarian berdasarkan nama atau deskripsi dokumen."
)


# ======================= #ANCHOR - REQUEST PARSER =========================== #

document_create_parser = ns.parser()

document_create_parser.add_argument(
    "document_name",
    type=str,
    required=True,
    location="form",
    help="Nama dokumen"
)

document_create_parser.add_argument(
    "description",
    type=str,
    required=False,
    location="form",
    help="Deskripsi dokumen"
)

document_create_parser.add_argument(
    "document",
    type=FileStorage,
    required=True,
    location="files",
    help="File legalitas yang akan diunggah"
)


document_edit_parser = ns.parser()

document_edit_parser.add_argument(
    "document_name",
    type=str,
    required=False,
    location="form",
    help="Nama dokumen"
)

document_edit_parser.add_argument(
    "description",
    type=str,
    required=False,
    location="form",
    help="Deskripsi dokumen"
)

document_edit_parser.add_argument(
    "document",
    type=FileStorage,
    required=False,
    location="files",
    help="File pengganti, jika ingin mengganti dokumen"
)


# ============================================================================ #
#                         #SECTION - LEGAL DOCUMENTS                           #
# ============================================================================ #

@ns.route("")
class LegalDocumentListResource(Resource):

    @jwt_required()
    @ns.expect(document_filter_parser)
    @measure_execution_time
    def get(self):
        """List Legal Documents"""

        filters = document_filter_parser.parse_args()

        data = get_legal_document_list_service(filters)

        return success(
            data=data,
            message="Daftar dokumen legalitas berhasil diambil"
        )

    @jwt_required()
    @ns.expect(document_create_parser)
    @measure_execution_time
    def post(self):
        """Create Legal Document"""

        args = document_create_parser.parse_args()

        body = {
            "document_name": args.get("document_name"),
            "description": args.get("description")
        }

        document = args.get("document")
        created_by = get_jwt().get("display_name")

        data = create_legal_document_service(
            body=body,
            created_by=created_by,
            document=document
        )

        return success(
            data=data,
            message="Dokumen legalitas berhasil ditambahkan"
        )


@ns.route("/<int:id_legal_document>")
class LegalDocumentDetailResource(Resource):

    @jwt_required()
    @measure_execution_time
    def get(self, id_legal_document):
        """Detail Legal Document"""

        data = get_legal_document_detail_service(
            id_legal_document
        )

        return success(
            data=data,
            message="Detail dokumen legalitas berhasil diambil"
        )

    @jwt_required()
    @ns.expect(document_edit_parser)
    @measure_execution_time
    def put(self, id_legal_document):
        """Update Legal Document"""

        # Ambil seluruh field teks dari multipart/form-data
        body = {
            "document_name": request.form.get("document_name", "").strip(),
            "description": request.form.get("description", "").strip(),
        }

        # Ambil file jika tersedia
        document = request.files.get("document")
        updated_by = get_jwt().get("display_name")

        # Debug sementara
        print("UPDATE LEGAL DOCUMENT")
        print("ID:", id_legal_document)
        print("BODY:", body)
        print("FILE:", document.filename if document else None)

        data = update_legal_document_service(
            id_legal_document=id_legal_document,
            body=body,
            updated_by=updated_by,
            document=document,
        )

        return success(
            data=data,
            message="Dokumen legalitas berhasil diperbarui",
        )

    @jwt_required()
    @measure_execution_time
    def delete(self, id_legal_document):
        """Delete Legal Document (Soft Delete)"""

        updated_by = get_jwt().get("display_name")

        delete_legal_document_service(
            id_legal_document=id_legal_document,
            updated_by=updated_by
        )

        return success(
            data=None,
            message="Dokumen legalitas berhasil dinonaktifkan"
        )
