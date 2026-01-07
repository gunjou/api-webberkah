# api/utils/decorator.py
import time
from functools import wraps
from flask_jwt_extended import verify_jwt_in_request, get_jwt

from api.shared.exceptions import ForbiddenError


def role_required(expected_roles):
    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            verify_jwt_in_request()
            jwt_data = get_jwt()
            role = jwt_data.get("account_type")
            if isinstance(expected_roles, (list, tuple, set)):
                if role not in expected_roles:
                    raise ForbiddenError("Role tidak diizinkan")
            else:
                if role != expected_roles:
                    raise ForbiddenError("Role tidak diizinkan")
            return fn(*args, **kwargs)
        return decorator
    return wrapper

def measure_execution_time(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        response = fn(*args, **kwargs)
        execution_time = round(
            (time.perf_counter() - start_time) * 1000,
            2
        )
        # response diasumsikan (body, status_code)
        if isinstance(response, tuple) and len(response) == 2:
            body, status = response
            if isinstance(body, dict):
                # ⬇️ FIX UTAMA ADA DI SINI
                meta = body.get("meta") or {}
                meta["execution_time_ms"] = execution_time
                body["meta"] = meta
            return body, status
        return response
    return wrapper