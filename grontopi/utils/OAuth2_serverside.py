from fastapi import HTTPException, status
from jose import JWTError, jwt, ExpiredSignatureError
from starlette.requests import Request

from config import conf



ALGORITHM = "HS256"

JWT_OPTIONS = {"verify_signature": True, "verify_aud": False}
RSA_KEY = {
    'kty': 'RSA',
    'n': conf.auth_server_n,
    'use': 'sig',
    'kid': conf.auth_server_kid,
    'e': 'AQAB'
}

CREDENTIALS_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials",
    headers={"WWW-Authenticate": "Bearer"},
)

CREDENTIALS_EXCEPTION_EMAIL = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Could not validate credentials email",
    headers={"WWW-Authenticate": "Bearer"},
)

EXPIRED_TOKEN_EXCEPTION = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Token is expired... ",
    headers={"WWW-Authenticate": "Bearer"},
)


def decode_token(token):
    if not token:
        raise CREDENTIALS_EXCEPTION
    if token == f"{conf.interservices_token}={conf.auth_server_kid}":
        return {
            "static_token": True,
            "resource_access": [],
            "roles": [],
            "email": conf.default_useremail
        }
    return jwt.decode(token, RSA_KEY, options=JWT_OPTIONS)


def found_access(search, info):
    for value in info.values():
        if search in value['roles']:
            return True
    return False


def apply_roles_rules(read, write, payload, request):
    if not read and not write:
        raise CREDENTIALS_EXCEPTION
    if (
            read and not found_access("lectura", payload["resource_access"])
    ):
        raise CREDENTIALS_EXCEPTION
    if write and not found_access("escritura", payload["resource_access"]):
        raise CREDENTIALS_EXCEPTION


def user_invalidator(read: bool = True, write: bool = False):
    async def verify_jwt_in_request(request: Request, read=read, write=write):
        if request.method in {"OPTIONS"} or not conf.use_OAuth2:
            return
        try:
            token = request.headers.get("Authorization", "")[7:]
            payload = decode_token(token)
            if not payload.get('static_token', False):
                apply_roles_rules(read, write, payload, request)
                return {
                    "static_token": False,
                    "resource_access": payload["resource_access"],
                    "roles": payload["realm_access"]["roles"],
                    "email": payload["email"]
                }
            return payload
        except ExpiredSignatureError:
            raise EXPIRED_TOKEN_EXCEPTION
        except JWTError:
            raise CREDENTIALS_EXCEPTION

    return verify_jwt_in_request
