from sqlalchemy import text

from api.utils.config import engine
from api.shared.helper import get_wita


# ============================================================================ #
#                         #SECTION - CLIENT                                  #
# ============================================================================ #

def get_client_list(filters: dict):

    sql = """
        SELECT
            c.id_client, c.code, c.name, c.address, c.phone, c.email, c.is_active, 
            c.created_by, c.updated_by, c.created_at, c.updated_at
        FROM client c
        WHERE 1 = 1
    """

    params = {}

    if filters.get("is_active") is not None:
        sql += """
            AND c.is_active = :is_active
        """
        params["is_active"] = int(filters["is_active"])
    else:
        sql += """
            AND c.is_active = 1
        """

    if filters.get("search"):
        sql += """
            AND (
                c.code ILIKE :search
                OR c.name ILIKE :search
            )
        """
        params["search"] = f"%{filters['search']}%"

    sql += """
        ORDER BY
            c.name ASC
    """

    with engine.connect() as conn:
        return conn.execute(
            text(sql),
            params
        ).mappings().all()


def get_client_by_id(id_client: int):

    sql = text("""
        SELECT
            id_client, code, name, address, phone, email, is_active
        FROM client
        WHERE
            id_client = :id_client
            AND is_active = 1
        LIMIT 1
    """)

    with engine.connect() as conn:
        return conn.execute(
            sql,
            {"id_client": id_client}
        ).mappings().first()


def get_client_by_code(code: str, id_client: int = None):

    sql = """
        SELECT
            id_client, code, name
        FROM client
        WHERE
            LOWER(code) = LOWER(:code)
            AND is_active = 1
    """

    params = {"code": code}

    if id_client:
        sql += """
            AND id_client != :id_client
        """
        params["id_client"] = id_client

    sql += """
        LIMIT 1
    """

    with engine.connect() as conn:
        return conn.execute(
            text(sql),
            params
        ).mappings().first()


def get_client_options():

    sql = text("""
        SELECT id_client, name FROM client WHERE is_active = 1 ORDER BY name ASC
    """)

    with engine.connect() as conn:
        return conn.execute(sql).mappings().all()


def get_client_detail(id_client: int):

    sql = text("""
        SELECT
            c.id_client, c.code, c.name, c.address, c.phone, c.email, c.is_active, 
            c.created_by, c.created_at, c.updated_by, c.updated_at
        FROM client c
        WHERE
            c.id_client = :id_client
            AND c.is_active = 1
        LIMIT 1
    """)

    with engine.connect() as conn:
        return conn.execute(
            sql,
            {"id_client": id_client}
        ).mappings().first()


def create_client(body: dict):

    sql = text("""
        INSERT INTO client (
            code, name, address, phone, email, created_by, created_at, updated_at
        )
        VALUES (
            :code, :name, :address, :phone, :email, :created_by, :now, :now
        )
        RETURNING id_client
    """)

    with engine.begin() as conn:
        result = conn.execute(
            sql,
            {
                "code": body["code"].strip(),
                "name": body["name"].strip(),
                "address": body.get("address"),
                "phone": body.get("phone"),
                "email": body.get("email"),
                "created_by": body["created_by"],
                "now": get_wita()
            }
        )

        return result.scalar()


def update_client(id_client: int, body: dict):

    sql = text("""
        UPDATE client
        SET
            code = :code,
            name = :name,
            address = :address,
            phone = :phone,
            email = :email,
            is_active = COALESCE(:is_active, is_active),
            updated_by = :updated_by,
            updated_at = :now
        WHERE
            id_client = :id_client
            AND is_active = 1
    """)

    with engine.begin() as conn:
        conn.execute(
            sql,
            {
                "id_client": id_client,
                "code": body["code"].strip(),
                "name": body["name"].strip(),
                "address": body.get("address"),
                "phone": body.get("phone"),
                "email": body.get("email"),
                "is_active": body.get("is_active"),
                "updated_by": body["updated_by"],
                "now": get_wita()
            }
        )


def delete_client(id_client: int, updated_by: str):

    sql_client = text("""
        UPDATE client
        SET
            is_active = 0,
            updated_by = :updated_by,
            updated_at = :now
        WHERE
            id_client = :id_client
            AND is_active = 1
    """)

    sql_client_pic = text("""
        UPDATE client_pic
        SET
            is_active = 0,
            updated_by = :updated_by,
            updated_at = :now
        WHERE
            id_client = :id_client
            AND is_active = 1
    """)

    now = get_wita()

    with engine.begin() as conn:

        conn.execute(
            sql_client,
            {
                "id_client": id_client,
                "updated_by": updated_by,
                "now": now
            }
        )

        conn.execute(
            sql_client_pic,
            {
                "id_client": id_client,
                "updated_by": updated_by,
                "now": now
            }
        )



# ============================================================================ #
#                         #SECTION - CLIENT PIC                              #
# ============================================================================ #

def get_all_client_pic():

    sql = text("""
        SELECT
            cp.id_client_pic,
            cp.id_client,

            c.code AS client_code,
            c.name AS client_name,

            cp.name,
            cp.position,
            cp.phone,
            cp.email,
            cp.is_active,

            cp.created_by,
            cp.created_at,
            cp.updated_by,
            cp.updated_at

        FROM client_pic cp

        INNER JOIN client c
            ON c.id_client = cp.id_client

        WHERE
            c.is_active = 1 AND cp.is_active = 1

        ORDER BY
            c.name ASC,
            cp.name ASC
    """)

    with engine.connect() as conn:
        return conn.execute(sql).mappings().all()


def get_client_pic_list(id_client: int):

    sql = text("""
        SELECT
            cp.id_client_pic, cp.id_client, cp.name, cp.position, cp.phone, cp.email, cp.is_active, 
            cp.created_by, cp.created_at, cp.updated_by, cp.updated_at
        FROM client_pic cp
        WHERE
            cp.id_client = :id_client
            AND cp.is_active = 1
        ORDER BY
            cp.name ASC
    """)

    with engine.connect() as conn:
        return conn.execute(
            sql,
            {"id_client": id_client}
        ).mappings().all()


def get_client_pic_by_id(id_client_pic: int):

    sql = text("""
        SELECT
            id_client_pic, id_client, name, position, phone, email, is_active
        FROM client_pic
        WHERE
            id_client_pic = :id_client_pic
            AND is_active = 1
        LIMIT 1
    """)

    with engine.connect() as conn:
        return conn.execute(
            sql,
            {"id_client_pic": id_client_pic}
        ).mappings().first()


def get_client_pic_detail(id_client_pic: int):

    sql = text("""
        SELECT
            cp.id_client_pic, cp.id_client, c.code AS client_code, c.name AS client_name, cp.name, cp.position,              cp.phone, cp.email, cp.is_active, cp.created_by, cp.created_at, cp.updated_by, cp.updated_at
        FROM client_pic cp
        INNER JOIN client c
            ON c.id_client = cp.id_client
        WHERE
            cp.id_client_pic = :id_client_pic
            AND cp.is_active = 1
            AND c.is_active = 1
        LIMIT 1
    """)

    with engine.connect() as conn:
        return conn.execute(
            sql,
            {"id_client_pic": id_client_pic}
        ).mappings().first()


def create_client_pic(body: dict):

    sql = text("""
        INSERT INTO client_pic (
            id_client, name, position, phone, email, created_by, created_at, updated_at
        )
        VALUES (
            :id_client, :name, :position, :phone, :email, :created_by, :now, :now
        )
        RETURNING id_client_pic
    """)

    with engine.begin() as conn:
        result = conn.execute(
            sql,
            {
                "id_client": body["id_client"],
                "name": body["name"].strip(),
                "position": body.get("position"),
                "phone": body.get("phone"),
                "email": body.get("email"),
                "created_by": body["created_by"],
                "now": get_wita()
            }
        )

        return result.scalar()


def update_client_pic(id_client_pic: int, body: dict):

    sql = text("""
        UPDATE client_pic
        SET
            name = :name,
            position = :position,
            phone = :phone,
            email = :email,
            is_active = COALESCE(:is_active, is_active),
            updated_by = :updated_by,
            updated_at = :now
        WHERE
            id_client_pic = :id_client_pic
            AND is_active = 1
    """)

    with engine.begin() as conn:
        conn.execute(
            sql,
            {
                "id_client_pic": id_client_pic,
                "name": body["name"].strip(),
                "position": body.get("position"),
                "phone": body.get("phone"),
                "email": body.get("email"),
                "is_active": body.get("is_active"),
                "updated_by": body["updated_by"],
                "now": get_wita()
            }
        )


def delete_client_pic(id_client_pic: int, updated_by: str):

    sql = text("""
        UPDATE client_pic
        SET
            is_active = 0,
            updated_by = :updated_by,
            updated_at = :now
        WHERE
            id_client_pic = :id_client_pic
            AND is_active = 1
    """)

    with engine.begin() as conn:
        conn.execute(
            sql,
            {
                "id_client_pic": id_client_pic,
                "updated_by": updated_by,
                "now": get_wita()
            }
        )
