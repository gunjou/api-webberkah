from flask import request
from flask_jwt_extended import jwt_required
from flask_restx import Namespace, Resource, reqparse
from werkzeug.datastructures import FileStorage

from api.shared.response import success
from api.shared.exceptions import ValidationError, NotFoundError
from api.utils.decorator import measure_execution_time
from api.utils.uploader import upload_document_to_cdn
from api.rcc.attachment.query import *


attachment_ns = Namespace("attachments", description="Attachment Management")

attachment_upload_parser = reqparse.RequestParser()
attachment_upload_parser.add_argument("file", type=FileStorage, location="files", required=True, help="File attachment")
attachment_upload_parser.add_argument("id_attachment_type", type=int, location="form", required=True, help="Jenis Attachment")
attachment_upload_parser.add_argument("keterangan", type=str, location="form")

@attachment_ns.route("/invoices/<int:id_invoice>/attachments")
class InvoiceAttachmentResource(Resource):
    @jwt_required()
    @attachment_ns.doc(consumes=["multipart/form-data"])
    @attachment_ns.expect(attachment_upload_parser)
    @measure_execution_time
    def post(self, id_invoice):
        """Upload Attachment"""

        args = (
            attachment_upload_parser
            .parse_args()
        )

        file = args["file"]

        if not file:
            raise ValidationError(
                "File wajib diupload"
            )

        uploaded = upload_document_to_cdn(
            file=file,
            category="invoice"
        )

        data = create_attachment(
            id_invoice=id_invoice,
            id_attachment_type=args[
                "id_attachment_type"
            ],

            nama_file=uploaded[
                "filename"
            ],

            path_file=uploaded[
                "url"
            ],

            ukuran_file=file.content_length,

            mime_type=uploaded[
                "mime_type"
            ],

            keterangan=args.get(
                "keterangan"
            )
        )

        return success(
            data=data,
            message="Attachment berhasil diupload"
        )


    @jwt_required()
    @measure_execution_time
    def get(self, id_invoice):
        """List Attachment"""

        data = get_attachment_list(
            id_invoice
        )

        return success(
            data=data,
            message="List attachment"
        )



@attachment_ns.route("/<int:id_attachment>")
class AttachmentDetailResource(Resource):
    @jwt_required()
    @measure_execution_time
    def get(self, id_attachment):
        """Detail Attachment"""

        data = get_attachment_by_id(
            id_attachment
        )

        if not data:
            raise NotFoundError(
                "Attachment tidak ditemukan"
            )

        return success(
            data=data,
            message="Detail attachment"
        )


    @jwt_required()
    @measure_execution_time
    def delete(self, id_attachment):
        """Delete Attachment"""

        existing = (
            get_attachment_by_id(
                id_attachment
            )
        )

        if not existing:
            raise NotFoundError(
                "Attachment tidak ditemukan"
            )

        delete_attachment(
            id_attachment
        )

        return success(
            message="Attachment berhasil dihapus"
        )
