# api/cashbook/category/query.py
from sqlalchemy import text

from api.utils.config import engine


# ============================================================================ #
#                      #SECTION - BASIC OPERATION CATEGORY                     #
# ============================================================================ #

# ========================== #ANCHOR - LIST CATEGORY ========================= #
def get_category_list():

    sql = text("""
        SELECT id_category, name, description, created_at, updated_at
        FROM categories
        WHERE is_active = 1 AND is_reportable = 1
        ORDER BY
            id_category ASC
    """)

    with engine.connect() as conn:
        return conn.execute(sql).mappings().all()


# ========================= #ANCHOR - DETAIL CATEGORY ======================== #
def get_category_detail(
    id_category: int
):

    sql = text("""
        SELECT id_category, name, description, created_at, updated_at
        FROM categories
        WHERE id_category = :id_category AND is_active = 1
    """)

    with engine.connect() as conn:
        return conn.execute(
            sql,
            {
                "id_category": id_category
            }
        ).mappings().first()


# ========================= #ANCHOR - CREATE CATEGORY ======================== #
def create_category(
    name: str,
    description: str = None
):

    sql = text("""
        INSERT INTO categories (name, description) 
        VALUES (:name, :description )
        RETURNING id_category
    """)

    with engine.begin() as conn:

        result = conn.execute(
            sql,
            {
                "name": name,
                "description": description
            }
        )

        return result.scalar()


# ========================= #ANCHOR - UPDATE CATEGORY ======================== #
def update_category(
    id_category: int,
    name: str,
    description: str = None
):

    sql = text("""
        UPDATE categories
        SET
            name = :name,
            description = :description,
            updated_at = CURRENT_TIMESTAMP
        WHERE
            id_category = :id_category
            AND is_active = 1
    """)

    with engine.begin() as conn:

        result = conn.execute(
            sql,
            {
                "id_category": id_category,
                "name": name,
                "description": description
            }
        )

        return result.rowcount


# ========================= #ANCHOR - DELETE CATEGORY ======================== #
def delete_category(
    id_category: int
):

    sql = text("""
        UPDATE categories
        SET
            is_active = 0,
            updated_at = CURRENT_TIMESTAMP
        WHERE
            id_category = :id_category
            AND is_active = 1
    """)

    with engine.begin() as conn:

        result = conn.execute(
            sql,
            {
                "id_category": id_category
            }
        )

        return result.rowcount
    
# ==================== #!SECTION - BASIC OPERATION CATEGORY ================== #