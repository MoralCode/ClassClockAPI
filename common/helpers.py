from flask import _request_ctx_stack, request, url_for, make_response, jsonify
from werkzeug.wrappers import Response
from functools import wraps
from jose import jwt
from six.moves.urllib.request import urlopen
import base64
from os import environ as env
import json
from uuid import UUID, uuid4
from datetime import datetime
from common.services import auth0management
import flask_limiter

import marshmallow
import marshmallow_jsonapi
import marshmallow_jsonapi.flask
import marshmallow_sqlalchemy

from common.constants import AuthType
from common.db_schema import db

from common.exceptions import Oops, AuthError
from common.schemas import Schema

AUTH0_DOMAIN = env.get("AUTH0_DOMAIN")
API_IDENTIFIER = env.get("API_IDENTIFIER")
ALGORITHMS = ["RS256"]

management_API = auth0management.Auth0ManagementService()

class JSONEncoder(json.JSONEncoder):
    # this was copied from https://github.com/miLibris/flask-rest-jsonapi/blob/ad3f90f81955fa41aaf0fb8c49a75a5fbe334f5f/flask_rest_jsonapi/utils.py under the terms of the MIT license.
    def default(self, obj):
        if isinstance(obj, datetime):
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

def new_patch_val(body_val, db_val):
    if body_val is not None and body_val != db_val:
        return body_val
    return db_val

#https: // github.com/rgant/saas-api-boilerplate/blob/d1599716eb77b4994781b465fec27c91f8721cb5/common/utilities.py  # L16
def camel_to_delimiter_separated(name, glue='_'):
    """
    Convert CamelCase to a delimiter-separated naming convention. Snake_case by default.
    :param str name: CamelCase name to convert
    :param str glue: Delimiter to use, default is an underscore for snake_case.
    :return str: delimiter-separated version of name
    """
    # From https://stackoverflow.com/a/1176023
    first_cap_re = re.compile('(.)([A-Z][a-z]+)')
    all_cap_re = re.compile('([a-z0-9])([A-Z])')
    replacement = fr'\1{glue}\2'
    ex = first_cap_re.sub(replacement, name)
    return all_cap_re.sub(replacement, ex).lower()

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


def make_jsonapi_error_object(code, error_id=None, title=None, message=None):
    """ Generates a JSON:API error response

    Arguments:
        code {number} -- The HTTP status code to return for the error; both through HTTP and in the JSON response.

    Keyword Arguments:
        title {string} -- An optional title for the error (i.e. "Unauthorized", "Access Denied") (default: {None})
        message {string} -- An optional message giving more details about the error (default: {None})

    Returns:
        A flask Response object for the web server
    """

    error_data = {'status': str(code)}

    if error_id is not None:
        error_data['id'] = error_id

    if title is not None:
        error_data['title'] = title

    if message is not None:
        error_data['detail'] = message

    return error_data


def make_jsonapi_response(response_data=None, code=None, headers={}):
    """ Forms a Flask-and-JSON:API-compatible JSON response

    Arguments:
        response_data {dict} -- The jsonapi object dict to return in the JSON response

    Keyword Arguments:
        code {number} -- The optional HTTP status code to return with the response (used for errors) (default: {None})
        headers {dict} -- A dict of optional headers to add to the response

    Returns:
        A flask Response object for the web server
    """

    content = {}
    content["jsonapi"] = {"version": "1.0"}

    if code is not None and (is_client_error(code) or is_server_error(code)):
        # error
        content['errors'] = response_data
    else:
        content["data"] = response_data

    if code is None:
        return make_response(json.dumps(content, cls=JSONEncoder), headers)
    else:
        return make_response(json.dumps(content, cls=JSONEncoder), code, headers)

def J(*args, **kwargs):
    """Wrapper around jsonify that sets the Content-Type of the response to
    application/vnd.api+json.
    """
    response = jsonify(*args, **kwargs)
    response.mimetype = "application/vnd.api+json"
    return response

def filter_dict(dict, filter, is_whitelist=True):
    return {key: val for key, val in dict.items() if ((key in filter) if is_whitelist else (key not in filter))}

def make_jsonapi_links_object(**kwargs):
    """Creates a JSON:API "links object" from a dict of data
    Returns:
        dict -- A links object dict with contents formatted per the JSON:API spec
    """
    links_object = {}
    for link_name in kwargs:
        links_object[link_name] = kwargs[link_name]

    return links_object


def make_jsonapi_resource_object(resource, attributes_schema, blueprint_name):
    """Creates a JSON:API "resource object" from a dict of data

    Arguments:
        data_dict {dict} -- The data to create the resource object from
        data_domain {string} -- A string describing what the data in data_dict represents (i.e. "school", "schedule", etc.)
        uri_function_name_mappings {dict} -- A mapping of the keys of identifiers in data_dict to the name of the function whose route should be used to generate URI's for responses
        TODO: maybe make uri_function_name_mappings an enum or something
    Raises:
        e: A Key Error if the data_dict somehow does not contain an "id" field. should never happen

    Returns:
        dict -- A resource object dict with contents formatted per the JSON:API spec
    """
    resource_object = {}
    resource_object["type"] = resource.type
    resource_object["id"] = resource.identifier

    resource_object["links"] = make_jsonapi_links_object(
        self=resource.get_uri(blueprint_name))

    resource_object["attributes"] = attributes_schema.dump(resource)

    if resource.type == "bellschedule":
        resource_object["relationships"] = {}
        resource_object["relationships"]["schools"] = {}
        resource_object["relationships"]["schools"]["links"] = make_jsonapi_links_object(self=url_for(
            blueprint_name + "." + blueprint_name + "_single_school", school_id=resource.school_id.hex, _external=True))

    return resource_object


def deconstruct_resource_object(resource_object):
    """extracts a more processable dict from a JSON:API "resource object" 

    Arguments:
        resource_object {dict} -- a dict in JSON:API format

    Returns:
        dict -- a flatter dict for easier processing
    """
    resource = {}
    resource["type"] = resource_object.get("type", None)
    resource["id"] = UUID(resource_object.get("id", uuid4().hex))

    return {**resource, **resource_object["attributes"]}


def handle_marshmallow_errors(errors):
    error_list = []
    for property_name, property_errors in errors.items():

        for value_type, input_errors in property_errors.items():

            for input_error in input_errors:

                message = input_error[:-1] + " provided to " + \
                    property_name + " of type " + value_type

                error = make_jsonapi_error_object(
                    400, title="Validation failure", message=message)
                error_list.append(error)

    return error_list, 400


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


def has_permission(permission):
    """Raises an AuthError if the specified scope is not present

    Arguments:
        scope {string} -- The scope to check

    Raises:
        AuthError: An authentication error
    """
    return
    if not permission in _request_ctx_stack.top.current_user.permissions:
        raise AuthError(
            "You do not have the necessary permission (" + permission.value + ") to access to this resource", 403)


def check_permissions(permissions_to_check):
    """Raises an AuthError if the specified scopes are not present

    Arguments:
        scope {string[]} -- A list of scopes to check

    Raises:
        AuthError: An authentication error
    """
    for perm in permissions_to_check:
        has_permission(perm)


def check_for_role(role):
    user_id = get_api_user_id()
    if user_id != "":
        return role in management_API.get_roles_for_user(user_id)
    else:
        return None


def check_ownership(cursor, school_id):
    cursor.execute(
        "SELECT owner_id FROM schools WHERE school_id=(UNHEX(%s))", (school_id,))
    # dict_keys_map defines the keys for the dictionary that is generated from the tuples returned from the database (so order matters)
    # dict_keys_map = ("id", "full_name", "acronym")

    owners = [owner_id[0] for owner_id in cursor]
    if get_api_user_id() not in owners:
        raise Oops("Authorizing user is not the owner of this school", 401)


def list_owned_school_ids(cursor, school_id):
    cursor.execute(
        "SELECT UNHEX(school_id) as id FROM schools WHERE owner_id=%s", (school_id,))
    # dict_keys_map defines the keys for the dictionary that is generated from the tuples returned from the database (so order matters)
    # dict_keys_map = ("id", "full_name", "acronym")

    return [sch_id[0] for sch_id in cursor]


# from https://stackoverflow.com/a/3675423


def replace_last(source_string, replace_what, replace_with):
    """Replaces only the last occurrence of a substring in a source string with a different string

    Arguments:
        source_string {string} -- The string perform the search on
        replace_what {string} -- The string to search for in the source string
        replace_with {string} -- The string to replace the search string for

    Returns:
        string -- The source string with the last occurrence of the replacement string replaces with the search string
    """
    head, _sep, tail = source_string.rpartition(replace_what)
    return head + replace_with + tail


def make_dict(the_tuple, keys):
    """Creates a dict from a pair of tuples of equal length

    Arguments:
        the_tuple {tuple} -- A tuple containing the data/values for the resulting dict
        keys {tuple (or maybe list)} -- A tuple containing the keys for the resulting dict

    Returns:
        A dict containing the data from both inputs
    """
    the_dict = {}
    for index, value in enumerate(the_tuple):
        key = keys[index]
        the_dict[key] = value

    return the_dict


def time_from_delta(delta):
    # print(type(delta))
    # print(type((datetime.min + delta)))
    return (datetime.min + delta).time().isoformat('minutes')


def extract_valid_credentials(encoded_credentials):
    """Extracts a username and password from a base64 encoded HTTP Authorization header

    Arguments:
        encoded_credentials {string} -- The raw/encoded HTTP Authorization header value

    Raises:
        Oops: A general Exception
        Oops: A general Exception

    Returns:
        list -- A list containing the decoded credentials in the form of [username, password] 
    """
    try:
        decoded = base64.b64decode(
            encoded_credentials).decode("utf-8").split(":")
    except:
        raise Oops("An error occured while decoding the credentials", 401)

    if len(decoded) != 2:
        raise Oops("credentials must not contain the ':' character", 401)

    return decoded


def get_comma_separated_string(the_list):
    """creates a string of comma-sepatated values from an input list

    Arguments:
        dictionary {[type]} -- [description]
    """
    output = ""

    for index, value in enumerate(the_list):
        output += value

        if index < len(the_list)-1:
            output += ", "
    return output


def build_sql_column_update_list(input_object, updateable_fields_schema, colname_mappings):

    sql_set = []
    values = ()

    json = updateable_fields_schema.dump(input_object).data
    # print(json)
    for field in json:
        if json[field] is not None:
            sql_set.append(
                (colname_mappings[field]
                 if field in colname_mappings else field) + "=%s"
            )
            values += (json[field],)

    return get_comma_separated_string(sql_set), values


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
            return f(*args, **kwargs)
        raise AuthError("Unable to find appropriate key", 401)
    return decorated


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
    """Check headers according to jsonapi reference
    :param callable func: the function to decorate
    :return callable: the wrapped function
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if request.method in ('POST', 'PATCH', 'PUT'):
            if 'Content-Type' in request.headers and request.headers['Content-Type'] != 'application/vnd.api+json':

                error = make_jsonapi_error_object(
                    message='Content-Type header must be application/vnd.api+json', title='Invalid request header', code=415)
                return make_jsonapi_response(response_data=error, code=415, headers={'Content-Type': 'application/vnd.api+json'})

        if 'Accept' in request.headers:
            for accept in request.headers['Accept'].split(','):
                if accept.strip() != 'application/vnd.api+json':

                    error = make_jsonapi_error_object(
                        message='Accept header must be application/vnd.api+json without media type parameters', title='Invalid request header', code=406)
                    return make_jsonapi_response(response_data=error, code=406, headers={'Content-Type': 'application/vnd.api+json'})

        return func(*args, **kwargs)

    return wrapper
