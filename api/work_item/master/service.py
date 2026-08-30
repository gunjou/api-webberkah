from api.shared.exceptions import ValidationError, NotFoundError
from .query import *


# ============================================================================ #
#                         #SECTION - CLIENT                                  #
# ============================================================================ #

def get_client_list_service(filters: dict):
    return get_client_list(filters)


def create_client_service(body: dict):

    if not body.get("code"):
        raise ValidationError("Client code wajib diisi.")

    if not body.get("name"):
        raise ValidationError("Nama client wajib diisi.")

    duplicate = get_client_by_code(body["code"])

    if duplicate:
        raise ValidationError("Client code sudah digunakan.")

    return create_client(body)


def get_client_options_service():

    return get_client_options()


def get_client_detail_service(id_client: int):

    client = get_client_detail(id_client)

    if not client:
        raise NotFoundError("Client tidak ditemukan.")

    return client


def update_client_service(id_client: int, body: dict):

    client = get_client_by_id(id_client)

    if not client:
        raise NotFoundError("Client tidak ditemukan.")

    if not body.get("code"):
        raise ValidationError("Client code wajib diisi.")

    if not body.get("name"):
        raise ValidationError("Nama client wajib diisi.")

    duplicate = get_client_by_code(
        body["code"],
        id_client=id_client
    )

    if duplicate:
        raise ValidationError("Client code sudah digunakan.")

    if body.get("is_active") not in (None, 0, 1):
        raise ValidationError("is_active hanya boleh bernilai 1 atau 0.")

    update_client(
        id_client=id_client,
        body=body
    )


def delete_client_service(id_client: int, updated_by: str):

    client = get_client_by_id(id_client)

    if not client:
        raise NotFoundError("Client tidak ditemukan.")

    delete_client(
        id_client=id_client,
        updated_by=updated_by
    )


# ============================================================================ #
#                         #SECTION - CLIENT PIC                              #
# ============================================================================ #

def get_all_client_pic_service():

    return get_all_client_pic()


def get_client_pic_list_service(id_client: int):

    client = get_client_by_id(id_client)

    if not client:
        raise NotFoundError("Client tidak ditemukan.")

    return get_client_pic_list(id_client)


def create_client_pic_service(body: dict):

    client = get_client_by_id(body["id_client"])

    if not client:
        raise NotFoundError("Client tidak ditemukan.")

    if not body.get("name"):
        raise ValidationError("Nama PIC wajib diisi.")

    return create_client_pic(body)


def get_client_pic_detail_service(id_client_pic: int):

    client_pic = get_client_pic_detail(id_client_pic)

    if not client_pic:
        raise NotFoundError("Client PIC tidak ditemukan.")

    return client_pic


def update_client_pic_service(id_client_pic: int, body: dict):

    client_pic = get_client_pic_by_id(id_client_pic)

    if not client_pic:
        raise NotFoundError("Client PIC tidak ditemukan.")

    if not body.get("name"):
        raise ValidationError("Nama PIC wajib diisi.")

    if body.get("is_active") not in (None, 0, 1):
        raise ValidationError("is_active hanya boleh bernilai 1 atau 0.")

    update_client_pic(
        id_client_pic=id_client_pic,
        body=body
    )


def delete_client_pic_service(id_client_pic: int, updated_by: str):

    client_pic = get_client_pic_by_id(id_client_pic)

    if not client_pic:
        raise NotFoundError("Client PIC tidak ditemukan.")

    delete_client_pic(
        id_client_pic=id_client_pic,
        updated_by=updated_by
    )