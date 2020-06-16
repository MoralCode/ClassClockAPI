from flask import _request_ctx_stack, request, url_for, make_response, jsonify
from werkzeug.wrappers import Response
from functools import wraps
from jose import jwt
from six.moves.urllib.request import urlopen
import base64
from os import environ as env
import json
from uuid import UUID, uuid4
from datetime import datetime, time
from common.services import auth0management
import flask_limiter
import re

import marshmallow
import marshmallow_sqlalchemy

from common.constants import AuthType, API_DATATYPE_HEADER, API_DATATYPE
from common.db_schema import db

from common.exceptions import Oops, AuthError

AUTH0_DOMAIN = env.get("AUTH0_DOMAIN")
API_IDENTIFIER = env.get("API_IDENTIFIER")
ALGORITHMS = ["RS256"]

management_API = auth0management.Auth0ManagementService()

class JSONEncoder(json.JSONEncoder):
    # this was copied from https://github.com/miLibris/flask-rest-jsonapi/blob/ad3f90f81955fa41aaf0fb8c49a75a5fbe334f5f/flask_rest_jsonapi/utils.py under the terms of the MIT license.
    def default(self, obj):
        if isinstance(obj, (datetime, time)):
            return obj.isoformat()
        elif isinstance(obj, UUID):
            return obj.hex
        elif isinstance(obj, bytearray):
            return obj.decode()
        return json.JSONEncoder.default(self, obj)


# status code helpers taken from https://github.com/flask-api/flask-api/blob/master/flask_api/status.py
def is_informational(code):
    return code >= 100 and code <= 199


def is_success(code):
    return code >= 200 and code <= 299


def is_redirect(code):
    return code >= 300 and code <= 399


def is_client_error(code):
    return code >= 400 and code <= 499


def is_server_error(code):
    return code >= 500 and code <= 599

def register_api(api, resource, api_version, name_of_optional_param='id', type_of_optional_param='string', url_prefix=""):
    name = resource.__name__.lower()
    url = "/" + name + "/"
    plural_url = "/" + name + "s/"

    version = api_version + "_"

    api.add_resource(
        resource,
        url_prefix + plural_url,
        endpoint=version + name + "_list",
        defaults={name_of_optional_param: None},
        methods=['GET', ]
    )
    api.add_resource(
        resource,
        url_prefix + plural_url,
        endpoint=version + "new_" + name,
        methods=['POST', ]
    )
    api.add_resource(
        resource,
        '%s<%s:%s>/' % (url_prefix + url, type_of_optional_param,
                        name_of_optional_param),
        endpoint=version + "single_" + name,
        methods=['GET', 'PUT', 'PATCH', 'DELETE']
    )


def make_error_object(code, error_id=None, title=None, message=None):
    """ Generates an error response object

    Arguments:
        code {number} -- The HTTP status code to return for the error; both through HTTP and in the JSON response.

    Keyword Arguments:
        title {string} -- An optional title for the error (i.e. "Unauthorized", "Access Denied") (default: {None})
        message {string} -- An optional message giving more details about the error (default: {None})

    Returns:
        an error JSON object 
    """

    error_data = {'status': str(code)}

    if error_id is not None:
        error_data['id'] = error_id

    if title is not None:
        error_data['title'] = title

    if message is not None:
        error_data['detail'] = message

    return error_data


def respond(response_data=None, code=200, headers=API_DATATYPE_HEADER):
    """ Forms the data into a JSON response

    Arguments:
        response_data {dict} -- The object dict to return in the JSON response

    Keyword Arguments:
        code {number} -- The optional HTTP status code to return with the response (used for errors) (default: {None})
        headers {dict} -- A dict of optional headers to add to the response

    Returns:
        A flask Response object for the web server
    """

    content = {}

    if code is not None and (is_client_error(code) or is_server_error(code)):
        # error
        content['errors'] = response_data
    else:
        content["data"] = response_data

    if code is None:
        return make_response(json.dumps(content, cls=JSONEncoder), headers)
    else:
        return make_response(json.dumps(content, cls=JSONEncoder), code, headers)


def trap_object_modified_since(obj_last_modification, since):
    if since > datetime.now():
        raise Oops("The date provided to the If-Modified-Since header cannot be in the future", 412, title="No Future Modification Dates")

    if since < obj_last_modification:
        raise Oops("The resource you are trying to change has been modified elsewhere", 412, title="Resource has been Modified")


def handle_marshmallow_errors(errors):
    error_list = []
    for property_name, property_errors in errors.items():

        for value_type, input_errors in property_errors.items():

            for input_error in input_errors:

                message = input_error[:-1] + " provided to " + \
                    property_name + " of type " + value_type

                error = make_error_object(
                    400, title="Validation failure", message=message)
                error_list.append(error)

    return error_list, 400


def get_request_body(request):
    """
    provides a central place to modify the data in the request body 
    """
    return request.get_json()

def get_request_origin_identifier():
    user_id_parts = get_api_user_id().split("|")
    return flask_limiter.util.get_remote_address() + get_api_client_id() + user_id_parts[1] if len(user_id_parts) > 2 else ""


def get_api_client_id():
    """Returns a string to group API calls together for the purposes of ratelimiting
    """
    # print(client_id)
    # print(type(client_id))
    if hasattr(_request_ctx_stack.top, 'current_user'):
        # get the "authorized party" field of the auth token payload (which should be the client ID)
        return _request_ctx_stack.top.current_user["azp"]
    else:
        return "Public"  # this is just a generic string to lump all unauthenticated requests together and ratelimit as one


def get_api_user_id():
    """Returns the id of the user for whom data is being accessed on behalf of
    """
    if hasattr(_request_ctx_stack.top, 'current_user'):
        raw_id = _request_ctx_stack.top.current_user["sub"]
        if raw_id.endswith("@clients"):
            return ""
        else:
            return raw_id
    else:
        return ""


def get_token_auth_header():
    return get_valid_auth_header_of_type(AuthType.TOKEN)


def get_valid_auth_header_of_type(auth_header_type):
    """Obtains a valid Authorization Header value
    """
    auth = request.headers.get("Authorization", None)
    if not auth:
        raise AuthError("Authorization header is expected", 401)

    parts = auth.split()

    if parts[0].lower() != auth_header_type.value.lower():
        raise AuthError("Authorization header value must start with " +
                        auth_header_type.value, 401)
    if len(parts) == 1:
        raise AuthError("Authorization header value is missing", 401)
    elif len(parts) > 2:
        raise AuthError("Authorization header must be in the format \"" +
                        auth_header_type.value + " [value]\"", 401)

    return parts[1]  # return the value provided with the token

def check_permissions(user, permissions_to_check):
    """Raises an AuthError if the specified scopes are not present

    Arguments:
        scope {string[]} -- A list of scopes to check

    Raises:
        AuthError: An authentication error
    """
# _request_ctx_stack.top.current_user
    perms_not_present = []
    for perm in permissions_to_check:
        if not perm in user.permissions:
           perms_not_present.append(perm)
    if perms_not_present != []:
        perms_needed = " ".join(perm.value for perm in perms_not_present)
        raise AuthError(
            "You have not been granted the necessary permissions to access to this resource. You are missing the following permissions: " + perms_needed, 403)


def check_for_role(role):
    user_id = get_api_user_id()
    if user_id != "":
        return role in management_API.get_roles_for_user(user_id)
    else:
        return None

def check_ownership(school):
    if get_api_user_id() not in school.owner_id:
        raise Oops("Authorizing user is not the owner of this school", 401)


def list_owned_school_ids(cursor, school_id):
    cursor.execute(
        "SELECT UNHEX(school_id) as id FROM schools WHERE owner_id=%s", (school_id,))
    # dict_keys_map defines the keys for the dictionary that is generated from the tuples returned from the database (so order matters)
    # dict_keys_map = ("id", "full_name", "acronym")

    return [sch_id[0] for sch_id in cursor]




#
# Decorators
#


def requires_auth(_func=None, *, permissions=None):
    """Determines if the access token is valid
    """
    # https://realpython.com/primer-on-python-decorators/#decorators-with-arguments
    def args_or_no(func):
        @wraps(func)
        def decorated(*args, **kwargs):
            token = get_token_auth_header()
            jsonurl = urlopen("https://"+AUTH0_DOMAIN+"/.well-known/jwks.json")
            jwks = json.loads(jsonurl.read())
            try:
                unverified_header = jwt.get_unverified_header(token)
            except jwt.JWTError:
                raise AuthError(
                    "Invalid token. Use an RS256 signed JWT Access Token", 401)
            if unverified_header["alg"] == "HS256":
                raise AuthError(
                    "Invalid token algorithm. Use an RS256 signed JWT Access Token", 401)
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
                    raise AuthError("Token has expired", 401)
                except jwt.JWTClaimsError:
                    raise AuthError(
                        "Incorrect JWT claims. Please check the audience and issuer", 401)
                except Exception:
                    raise AuthError("Unable to parse authentication token.", 401)

                _request_ctx_stack.top.current_user = payload

                #this permissions check was added separately from the auth0 validation code 
                if permissions is not None:
                    check_permissions(payload, permissions)

                return func(*args, **kwargs)

            raise AuthError("Unable to find appropriate key", 401)
        return decorated

    if _func is None:
        return args_or_no
    else:
        return args_or_no(_func)



def requires_admin(f):
    """Determines if the user has the correct admin permissions for an action 
    """
    @wraps(f)
    def decorated(*args, **kwargs):

        is_admin = check_for_role("admin")
        if is_admin is None:
            raise Oops("There must be a user signed in to perform this action",
                       400, title="No User Authorization")
        elif not is_admin:
            raise Oops("Authorizing user does not have the correct role to perform this action",
                       401, title="Incorrect User Role")
        else:
            return f(*args, **kwargs)
    return decorated

# decorator modified from https://github.com/miLibris/flask-rest-jsonapi/blob/ad3f90f81955fa41aaf0fb8c49a75a5fbe334f5f/flask_rest_jsonapi/decorators.py
def check_headers(func):
    """decorator that provides a place to check headers
    :param callable func: the function to decorate
    :return callable: the wrapped function
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if request.method in ('POST', 'PATCH', 'PUT'):
            if 'Content-Type' in request.headers and request.headers['Content-Type'] != API_DATATYPE:
                error = make_error_object(
                    message='Content-Type header must be ' + API_DATATYPE, title='Invalid request header', code=415)
                return respond(response_data=error, code=415)

        if 'Accept' in request.headers:
            for accept in request.headers['Accept'].split(','):
                if accept.strip() != API_DATATYPE:
                    error = make_error_object(
                        message='Accept header must be ' + API_DATATYPE, title='Invalid request header', code=406)
                    return respond(response_data=error, code=406)

        return func(*args, **kwargs)

    return wrapper
