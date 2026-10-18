
from sqlalchemy import text

from api.utils.config import engine
from api.shared.helper import get_wita


# ============================================================================ #
#                         #SECTION - LEGAL DOCUMENTS                           #
# ============================================================================ #

def get_legal_document_list(search=None):

    conditions = [
        "is_active = 1"
    ]

    params = {}

    # ================================== Search ================================== #

    if search:
        conditions.append("""
            (
                LOWER(document_name) LIKE LOWER(:search)
                OR LOWER(COALESCE(description, '')) LIKE LOWER(:search)
            )
        """)

        params["search"] = f"%{search.strip()}%"

    where_clause = " AND ".join(conditions)

    # ================================ Count Query =============================== #

    count_query = text(f"""
        SELECT COUNT(*)
        FROM legal_documents
        WHERE {where_clause}
    """)

    # ================================ Data Query ================================ #

    query = text(f"""
        SELECT
            id_legal_document,
            document_name,
            description,
            file_url,
            is_active,
            created_by,
            created_at,
            updated_by,
            updated_at
        FROM legal_documents
        WHERE {where_clause}
        ORDER BY
            document_name ASC,
            id_legal_document DESC
    """)

    with engine.connect() as conn:

        total = conn.execute(
            count_query,
            params
        ).scalar()

        result = conn.execute(
            query,
            params
        ).mappings().all()

    return {
        "items": [dict(row) for row in result],
        "total": total
    }


def get_legal_document_by_id(id_legal_document):

    query = text("""
        SELECT
            id_legal_document,
            document_name,
            description,
            file_url,
            is_active,
            created_by,
            created_at,
            updated_by,
            updated_at
        FROM legal_documents
        WHERE
            id_legal_document = :id_legal_document
            AND is_active = 1
    """)

    with engine.connect() as conn:

        result = conn.execute(
            query,
            {
                "id_legal_document": id_legal_document
            }
        ).mappings().first()

    return dict(result) if result else None


def create_legal_document(
    document_name,
    description,
    file_url,
    created_by
):

    now = get_wita()

    query = text("""
        INSERT INTO legal_documents (
            document_name,
            description,
            file_url,
            is_active,
            created_by,
            created_at,
            updated_at
        )
        VALUES (
            :document_name,
            :description,
            :file_url,
            1,
            :created_by,
            :created_at,
            :updated_at
        )
        RETURNING id_legal_document
    """)

    with engine.begin() as conn:

        result = conn.execute(
            query,
            {
                "document_name": document_name,
                "description": description,
                "file_url": file_url,
                "created_by": created_by,
                "created_at": now,
                "updated_at": now
            }
        ).mappings().first()

    return {
        "id_legal_document": result["id_legal_document"]
    }




def update_legal_document(
    id_legal_document,
    document_name,
    description,
    file_url,
    updated_by,
    update_description=False
):

    now = get_wita()

    query = text("""
        UPDATE legal_documents
        SET
            document_name = COALESCE(
                :document_name,
                document_name
            ),
            description = CASE
                WHEN :update_description
                    THEN :description
                ELSE description
            END,
            file_url = COALESCE(
                :file_url,
                file_url
            ),
            updated_by = :updated_by,
            updated_at = :updated_at
        WHERE
            id_legal_document = :id_legal_document
            AND is_active = 1
        RETURNING id_legal_document
    """)

    with engine.begin() as conn:

        result = conn.execute(
            query,
            {
                "id_legal_document": id_legal_document,
                "document_name": document_name,
                "description": description,
                "file_url": file_url,
                "updated_by": updated_by,
                "updated_at": now,
                "update_description": update_description
            }
        ).mappings().first()

    return {
        "id_legal_document": result["id_legal_document"]
    } if result else None



def delete_legal_document(
    id_legal_document,
    updated_by
):

    now = get_wita()

    query = text("""
        UPDATE legal_documents
        SET
            is_active = 0,
            updated_by = :updated_by,
            updated_at = :updated_at
        WHERE
            id_legal_document = :id_legal_document
            AND is_active = 1
        RETURNING id_legal_document
    """)

    with engine.begin() as conn:

        result = conn.execute(
            query,
            {
                "id_legal_document": id_legal_document,
                "updated_by": updated_by,
                "updated_at": now
            }
        ).mappings().first()

    return {
        "id_legal_document": result["id_legal_document"]
    } if result else None
