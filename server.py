from functools import wraps
import json
from os import environ as env
from six.moves.urllib.request import urlopen

from dotenv import load_dotenv, find_dotenv
from flask import Flask, request, abort, make_response, jsonify, _request_ctx_stack
from werkzeug.exceptions import HTTPException
from flask_cors import cross_origin
from flask_limiter import Limiter
# from flask_limiter.util import get_remote_address
from jose import jwt
from pymongo import MongoClient
from bson import json_util
from enum import Enum
import http.client, base64
from flasgger import Swagger
#
# ENUMS, classes, and shortcut methods
#

class AuthType(Enum):
    TOKEN="Bearer"
    CREDENTIALS="Basic"

# Format error response and append status code.
class AuthError(Exception):
    def __init__(self, error, status_code):
        self.error = error
        self.status_code = status_code


def get_API_user_identifier():
    # print(client_id)
    # print(type(client_id))
    if hasattr(_request_ctx_stack.top, 'current_user'):
        return _request_ctx_stack.top.current_user["azp"] # get the "authorized party" field of the auth token payload (which should be the client ID)
    else:
        return "Public"





# 
# App Setup 
#

AUTH0_DOMAIN = env.get("AUTH0_DOMAIN")
API_IDENTIFIER = env.get("API_IDENTIFIER")
MONGODB_CREDS = env.get("MONGODB_CONN_STRING")
ALGORITHMS = ["RS256"]


client = MongoClient(MONGODB_CREDS)
db=client.admin

app = Flask(__name__)
limiter = Limiter(app, default_limits=["25/hour", "5/minute"], key_func = get_API_user_identifier)
swagger = Swagger(app, config={
    "headers": [
    ],
    "specs": [
        {
            "endpoint": 'apispec_1',
            "route": '/apispec_1.json',
            "rule_filter": lambda rule: True,  # all in
            "model_filter": lambda tag: True,  # all in
        }
    ],
    "static_url_path": "/flasgger_static",
    # "static_folder": "static",  # must be set by user
    "swagger_ui": True,
    "specs_route": "/docs/"
})

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

    
    return parts[1] #return the value provided with the token


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

def extract_valid_credentials(encoded_credentials):    
    try:
        decoded = base64.b64decode(encoded_credentials).decode("utf-8").split(":")
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



#
# Routes
#

@app.route("/v1/public")
@cross_origin(headers=["Content-Type", "Authorization"])
def public():
    """No access token required to access this route
    """
    response = "Hello from a public endpoint! You don't need to be authenticated to see this."
    return jsonify(message=response)


@app.route("/v1/private")
@cross_origin(headers=["Content-Type", "Authorization"])
@cross_origin(headers=["Access-Control-Allow-Origin", "http://localhost:3000"])
@requires_auth
def private():
    """A valid access token is required to access this route
    """
    response = "Hello from a private endpoint! You need to be authenticated to see this."
    return jsonify(message=response)


@app.route("/v1/private-scoped")
@cross_origin(headers=["Content-Type", "Authorization"])
@cross_origin(headers=["Access-Control-Allow-Origin", "http://localhost:3000"])
@requires_auth
def private_scoped():
    """A valid access token and an appropriate scope are required to access this route
    """
    check_scope("read:messages")

    response = "Hello from a private endpoint! You need to be authenticated and have a scope of read:messages to see this."
    return jsonify(message=response)


@app.route("/v1/token")
@cross_origin(headers=["Content-Type", "Authorization"])
@limiter.limit("10 per day")
def get_token():
    """Get an access token to use for authenticating to other endpoints
    """

    credentials = extract_valid_credentials(
        get_valid_auth_header_of_type(AuthType.CREDENTIALS)
        )

    conn = http.client.HTTPSConnection(AUTH0_DOMAIN)

    payload = json.dumps({
        "client_id":credentials[0],
        "client_secret":credentials[1],
        "audience":API_IDENTIFIER,
        "grant_type":"client_credentials"
        })

    conn.request("POST", "/oauth/token", payload, { 'content-type': "application/json" })

    response = conn.getresponse().read().decode("utf-8")
    conn.close()
    return response




#
#
#   Error Handler Section
#
#

#override default rate limit exceeded error and return a JSON response instead
#https://flask-limiter.readthedocs.io/en/stable/#custom-rate-limit-exceeded-responses
@app.errorhandler(429)
def ratelimit_handler(e):
    return make_response(
            jsonify(error="ratelimit exceeded %s" % e.description),
            429
            )


@app.errorhandler(AuthError)
def handle_auth_error(ex):
    response = jsonify(ex.error)
    response.status_code = ex.status_code
    return response

@app.errorhandler(HTTPException)
def handle_HTTP_error(e):
    code = 500
    if isinstance(e, HTTPException):
        code = e.code
    return make_response(
            jsonify(error=str(code) + " " + e.name, message=e.description),
            404
            )

if __name__ == "__main__":
    app.run() #    app.run(host="0.0.0.0", port=env.get("PORT", 3010))

