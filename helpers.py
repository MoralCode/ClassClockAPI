from flask import _request_ctx_stack, request, url_for
from functools import wraps
from jose import jwt
from enum import Enum
from bson.objectid import ObjectId
import base64


#
# ENUMS, classes, and shortcut methods
#


class AuthType(Enum):
    TOKEN = "Bearer"
    CREDENTIALS = "Basic"

# Format error response and append status code.


class AuthError(Exception):
    def __init__(self, error, status_code):
        self.error = error
        self.status_code = status_code


def get_API_user_identifier():
    # print(client_id)
    # print(type(client_id))
    if hasattr(_request_ctx_stack.top, 'current_user'):
        # get the "authorized party" field of the auth token payload (which should be the client ID)
        return _request_ctx_stack.top.current_user["azp"]
    else:
        return "Public"


#
# Helpers
#


def get_token_auth_header():
    return get_valid_auth_header_of_type(AuthType.TOKEN)


def get_valid_auth_header_of_type(auth_header_type):
    """Obtains the access token from the Authorization Header
    """
    auth = request.headers.get("Authorization", None)
    if not auth:
        raise AuthError({"code": "authorization_header_missing",
                         "description":
                         "Authorization header is expected"}, 401)

    parts = auth.split()

    if parts[0].lower() != auth_header_type.value.lower():
        raise AuthError({"code": "invalid_header",
                         "description":
                         "Authorization header value must start with " +
                         auth_header_type.value}, 401)
    if len(parts) == 1:
        raise AuthError({"code": "invalid_header",
                         "description": "Header value is missing"}, 401)
    elif len(parts) > 2:
        raise AuthError({"code": "invalid_header",
                         "description":
                         "Authorization header must be in the format \"" +
                         auth_header_type.value + " [value]\""}, 401)

    return parts[1]  # return the value provided with the token


def scope_is_present(scope_to_check):
    """Determines if the required scope is present in the access token
    Args:
        scope_to_check (str): The scope required to access the resource
    """
    token = get_token_auth_header()
    unverified_claims = jwt.get_unverified_claims(token)
    if unverified_claims.get("scope"):
        token_scopes = unverified_claims["scope"].split()
        for token_scope in token_scopes:
            if token_scope == scope_to_check:
                return True
    return False


def check_scope(scope):
    if not scope_is_present(scope):
        raise AuthError({
            "code": "Unauthorized",
            "description": "Access to this resource requires the " + scope + " scope"
        }, 403)

# from https://blog.miguelgrinberg.com/post/designing-a-restful-api-with-python-and-flask


def get_uri(identifier, url_function_name):
    """ returns a URI given an id and the function name of the endpoint
    """
    return url_for(url_function_name, identifier=identifier, _external=True)


def id_to_uri(resource, url_function_name):
    """ Replaces the ID field in resource with its URI
    """
    new_resource = {}
    for field in resource:
        if field in ['id', '_id']:

            identifier = resource[field]
            if type(identifier) is ObjectId:
                identifier = str(resource[field])

            new_resource['uri'] = get_uri(identifier, url_function_name)
        else:
            new_resource[field] = resource[field]
    return new_resource


def extract_valid_credentials(encoded_credentials):
    try:
        decoded = base64.b64decode(
            encoded_credentials).decode("utf-8").split(":")
    except:
        abort(401, "An error occured while decoding the credentials")

    if len(decoded) != 2:
        abort(401, "credentials must not contain the ':' character")

    return decoded


#
# Decorators
#

def requires_auth(f):
    """Determines if the access token is valid
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = get_token_auth_header()
        jsonurl = urlopen("https://"+AUTH0_DOMAIN+"/.well-known/jwks.json")
        jwks = json.loads(jsonurl.read())
        try:
            unverified_header = jwt.get_unverified_header(token)
        except jwt.JWTError:
            raise AuthError({"code": "invalid_header",
                             "description":
                             "Invalid header. "
                             "Use an RS256 signed JWT Access Token"}, 401)
        if unverified_header["alg"] == "HS256":
            raise AuthError({"code": "invalid_header",
                             "description":
                             "Invalid header. "
                             "Use an RS256 signed JWT Access Token"}, 401)
        rsa_key = {}
        for key in jwks["keys"]:
            if key["kid"] == unverified_header["kid"]:
                rsa_key = {
                    "kty": key["kty"],
                    "kid": key["kid"],
                    "use": key["use"],
                    "n": key["n"],
                    "e": key["e"]
                }
        if rsa_key:
            try:
                payload = jwt.decode(
                    token,
                    rsa_key,
                    algorithms=ALGORITHMS,
                    audience=API_IDENTIFIER,
                    issuer="https://"+AUTH0_DOMAIN+"/"
                )
            except jwt.ExpiredSignatureError:
                raise AuthError({"code": "token_expired",
                                 "description": "token is expired"}, 401)
            except jwt.JWTClaimsError:
                raise AuthError({"code": "invalid_claims",
                                 "description":
                                 "incorrect claims,"
                                 " please check the audience and issuer"}, 401)
            except Exception:
                raise AuthError({"code": "invalid_header",
                                 "description":
                                 "Unable to parse authentication"
                                 " token."}, 401)

            _request_ctx_stack.top.current_user = payload
            return f(*args, **kwargs)
        raise AuthError({"code": "invalid_header",
                         "description": "Unable to find appropriate key"}, 401)
    return decorated