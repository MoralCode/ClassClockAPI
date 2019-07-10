from flask import _request_ctx_stack, request, url_for, make_response, jsonify
from werkzeug.wrappers import Response
from functools import wraps
from jose import jwt
from six.moves.urllib.request import urlopen
import base64
from os import environ as env
import json
from flask_restful import Resource

from common.jsonapi.utils import JSONEncoder
from common.jsonapi.errors import jsonapi_errors


from common.constants import AuthType


AUTH0_DOMAIN = env.get("AUTH0_DOMAIN")
API_IDENTIFIER = env.get("API_IDENTIFIER")
ALGORITHMS = ["RS256"]

# Format error response and append status code.


class AuthError(Exception):
    def __init__(self, error, status_code):
        self.error = error
        self.status_code = status_code


class Oops(Exception):
    def __init__(self, message, status_code):
        self.message = message
        self.status_code = status_code


#status code helpers taken from https://github.com/flask-api/flask-api/blob/master/flask_api/status.py
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


def make_jsonapi_response(data=None, code=None, **kwargs):
    """ Forms a Flask-and-JSON:API-compatible JSON response

    Arguments:
        data {dict} -- The content to pass to the API client in the JSON response

    Keyword Arguments:
        code {number} -- The optional HTTP status code to return with the response (used for errors) (default: {None})
        kwargs -- all other parameters to be passed through to the response

    Returns:
        A flask Response object for the web server
    """
    headers = {'Content-Type': 'application/vnd.api+json'}
    content = data

    if code is None:
        return make_response(json.dumps(content, cls=JSONEncoder), headers)

    # code is not none if execution reaches here

    if is_client_error(code) or is_server_error(code):
        # error
        content = jsonapi_errors([make_jsonapi_error_object(code, **kwargs)])

    return make_response(json.dumps(content, cls=JSONEncoder), code, headers)


def make_jsonapi_resource_object(data_dict, data_domain, uri_function_name_mappings):
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

    # data_domain is a string to describe the type of data (i.e. school, schedule, etc.) for use as the key in the JSON response
    resource_object["type"] = str(data_domain)

    resource_object["links"] = get_self_link(
        data_dict, uri_function_name_mappings)

    relationships = get_relationships(data_dict, uri_function_name_mappings)

    if relationships is not None:
        resource_object["relationships"] = relationships

    resource_object["attributes"] = {}

    # data is expected to be a dict, not a tuple straight from the database
    for field in data_dict:
        if field == "id":
            try:
                resource_object["id"] = data_dict["id"]
            except KeyError as e:
                # TODO: this is an internal error so im not 100% sure if it should be passed through to the api client as is or just be logged and generalized as a 500 internal server error
                print(
                    "An id field is required in the data dict passed to make_jsonapi_resource_object, but none was found.")
                raise e
        else:
            resource_object["attributes"][field] = data_dict[field]

    return resource_object


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
    """Raises an AuthError if the specified scope is not present

    Arguments:
        scope {string} -- The scope to check

    Raises:
        AuthError: An authentication error
    """
    if not scope_is_present(scope):
        raise AuthError(
            "Access to this resource requires the " + scope + " scope", 403)


def check_scopes(scopes):
    """Raises an AuthError if the specified scopes are not present

    Arguments:
        scope {string[]} -- A list of scopes to check

    Raises:
        AuthError: An authentication error
    """
    for scope in scopes:
        check_scope(scope)

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


# from https://blog.miguelgrinberg.com/post/designing-a-restful-api-with-python-and-flask


def get_uri(identifier, uri_function_name, absolute_uri=True):
    """Returns a URI given an identifier and the function name of the endpoint

    Arguments:
        identifier {string} -- The resource's identifier to substitute into the uri 
        uri_function_name {string} -- The name of the function whose route should be used to generate URI's for responses

    Keyword Arguments:
        absolute_uri {bool} -- A flag indicating whether to return an absolute URI (https://example.com/endpoint) or a relative URI (/endpoint) (default: {True})

    Returns:
        string -- The URI for the resource
    """
    return url_for(uri_function_name, identifier=identifier, _external=absolute_uri)


def get_self_link(resource, uri_function_name_mappings):
    """Returns the URI to the provided resource as a JSON:API "links object"

    Arguments:
        resource {dict} -- The data to create the links object from
        uri_function_name_mappings {dict} -- A mapping of the keys of identifiers in resource to the name of the function whose route should be used to generate URI's for responses

    Returns:
        dict -- A links object dict with contents formatted per the JSON:API spec
    """
    links = {}
    if "id" in resource:

        identifier = resource["id"]

        links["self"] = get_uri(
            identifier, uri_function_name_mappings["id"], True)
    else:
        return None

    return links


def get_relationships(resource, uri_function_name_mappings):
    """Returns the URIs to related resources as a JSON:API "relationships object"

    Arguments:
        resource {dict} -- The data to create the relationships object from
        uri_function_name_mappings {dict} -- A mapping of the keys of identifiers in resource to the name of the function whose route should be used to generate URI's for responses

    Returns:
        dict -- A relationships object dict with contents formatted per the JSON:API spec
    """
    relationships = {}
    for field in resource:
        if field.endswith("_id"):

            identifier = resource[field]

            resource_name = replace_last(field, "_id", "")

            # got to initialize all the things or python will get angry
            relationships[resource_name] = {}
            relationships[resource_name]["links"] = {}
            relationships[resource_name]["links"]["self"] = get_uri(
                identifier, uri_function_name_mappings[field], True)

    return relationships if relationships != {} else None


def make_dict(the_tuple, keys):
    """Creates a dict from a pair of tuples of equal length

    Arguments:
        the_tuple {tuple} -- A tuple containing the data/values for the resulting dict
        keys {tuple (or maybe list)} -- A tuple containing the keys for the resulting dict

    Returns:
        A dict containing the data from both inputs
    """
    the_dict = {}
    for value in the_tuple:
        key = keys[the_tuple.index(value)]
        the_dict[key] = value if not isinstance(
            value, bytearray) else value.decode()
    return the_dict


def make_jsonapi_success_response(data, data_domain_string, uri_function_name_mappings):
    """Generates a JSON:API success response

    Arguments:
        data {dict} -- The data to create the response from
        data_domain_string {string} -- A string describing what the data in the data parameter represents (i.e. "school", "schedule", etc.)
        uri_function_name_mappings {dict} -- A mapping of the keys of identifiers in `data` to the name of the function whose route should be used to generate URI's for responses

    Returns:
        A flask Response object for the web server
    """
    response_content = {}
    response_content["jsonapi"] = {"version": "1.0"}

    if isinstance(data, list):
        response_content["data"] = []

        for item in data:
            response_content["data"].append(
                make_jsonapi_resource_object(
                    item, data_domain_string, uri_function_name_mappings)
            )
    else:
        response_content["data"] = make_jsonapi_resource_object(
            data, data_domain_string, uri_function_name_mappings)

    response_content["links"] = get_self_link(
        data, uri_function_name_mappings)

    return make_jsonapi_response(response_content)


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


# decorator modified from https://github.com/miLibris/flask-rest-jsonapi/blob/ad3f90f81955fa41aaf0fb8c49a75a5fbe334f5f/flask_rest_jsonapi/decorators.py
def check_headers(func):
    """Check headers according to jsonapi reference
    :param callable func: the function to decorate
    :return callable: the wrapped function
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if request.method in ('POST', 'PATCH'):
            if 'Content-Type' in request.headers and\
                    'application/vnd.api+json' in request.headers['Content-Type'] and\
                    request.headers['Content-Type'] != 'application/vnd.api+json':

                return make_jsonapi_error_response(415,
                                                   title="Invalid request header", message="Content-Type header must be application/vnd.api+json")
        if 'Accept' in request.headers:
            flag = False
            for accept in request.headers['Accept'].split(','):
                if accept.strip() == 'application/vnd.api+json':
                    flag = False
                    break
                if 'application/vnd.api+json' in accept and accept.strip() != 'application/vnd.api+json':
                    flag = True
            if flag is True:

                return make_jsonapi_error_response(406,
                                                   title="Invalid request header", message="Accept header must be application/vnd.api+json without media type parameters")
        return func(*args, **kwargs)

    return wrapper

# this has to be below requires_auth


class AuthenticatedResource(Resource):
    decorators = [requires_auth]   # applies to all inherited resources
