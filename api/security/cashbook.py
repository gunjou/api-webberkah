# api/security/cashbook.py
from functools import wraps
from flask_jwt_extended import verify_jwt_in_request, get_jwt

from api.shared.exceptions import ForbiddenError


def cashbook_role_required():

    def wrapper(fn):

        @wraps(fn)
        def decorator(*args, **kwargs):

            verify_jwt_in_request()

            jwt = get_jwt()

            if jwt.get("account_type") != "admin":
                raise ForbiddenError(
                    "Hanya admin yang dapat mengakses Cashbook."
                )

            if jwt.get("role") not in [
                "SUPER_ADMIN",
                "FINANCE"
            ]:
                raise ForbiddenError(
                    "Role tidak memiliki akses ke Cashbook."
                )

            return fn(*args, **kwargs)

        return decorator

    return wrapper