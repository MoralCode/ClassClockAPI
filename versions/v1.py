import json
from os import environ as env
from six.moves.urllib.request import urlopen

from flask import Blueprint, abort, make_response, jsonify
from werkzeug.exceptions import HTTPException
from flask_cors import cross_origin

from pymongo import MongoClient
from bson import json_util
from bson.objectid import ObjectId
import http.client

from helpers import requires_auth, check_scope, AuthError, id_to_uri, build_response
from constants import APIScopes
#
# App Setup
#
AUTH0_DOMAIN = env.get("AUTH0_DOMAIN")
API_IDENTIFIER = env.get("API_IDENTIFIER")
MONGODB_CREDS = env.get("MONGODB_CONN_STRING")
ALGORITHMS = ["RS256"]


client = MongoClient(MONGODB_CREDS)
db = client.classclock
schools = db.schools

blueprint = Blueprint('v1', __name__)


#
# Routes
#

# @blueprint.route("/public")
# @cross_origin(headers=["Content-Type", "Authorization"])
# def public():
#     """No access token required to access this route
#     """
#     response = "Hello from a public endpoint! You don't need to be authenticated to see this."
#     return jsonify(message=response)


# @blueprint.route("/private")
# @cross_origin(headers=["Content-Type", "Authorization"])
# @cross_origin(headers=["Access-Control-Allow-Origin", "http://localhost:3000"])
# @requires_auth
# def private():
#     """A valid access token is required to access this route
#     """
#     response = "Hello from a private endpoint! You need to be authenticated to see this."
#     return jsonify(message=response)


# @blueprint.route("/private-scoped")
# @cross_origin(headers=["Content-Type", "Authorization"])
# @cross_origin(headers=["Access-Control-Allow-Origin", "http://localhost:3000"])
# @requires_auth
# def private_scoped():
#     """A valid access token and an appropriate scope are required to access this route
#     """
#     print("hi")
#     check_scope("read:messages")

#     response = "Hello from a private endpoint! You need to be authenticated and have a scope of read:messages to see this."
#     return jsonify(message=response)


@blueprint.route("/schools", methods=['GET'])
@cross_origin(headers=["Content-Type", "Authorization"])
@cross_origin(headers=["Access-Control-Allow-Origin", "http://localhost:5000"])
@requires_auth
def get_schools():
    """Get a list of every publicly accessible ClassClock school
    ---
    responses:
        '200':
            description: A list of every publicly accessible ClassClock school
        '400':
            description: Unauthorized for some reason such as an invalid access token or incorrect scopes
    """
    check_scope(APIScopes.READ_ALL_SCHOOLS)

    schoolData = {}

    for school in schools.find():

        schoolData[str(school["_id"])] = build_response(
            school, ["id", "fullName", "acronym"], "v1.get_school_by_id")

    return jsonify({"schoolsByID": schoolData})


@blueprint.route("/school/<string:identifier>", methods=['GET'])
@cross_origin(headers=["Content-Type", "Authorization"])
@cross_origin(headers=["Access-Control-Allow-Origin", "http://localhost:5000"])
@requires_auth
def get_school_by_id(identifier):
    """
    Get information about a single school
    ---
    parameters:
    - name: identifier
      in: path
      type: string
      required: true
      description: the identifier string of the school you are requesting
    responses:
        200:
            description: data for a single school
        '400':
            description: Unauthorized for some reason such as an invalid access token or incorrect scopes
        default:
            description: error payload

    """

    school = schools.find_one({"_id": ObjectId(identifier)})

    return jsonify(build_response(school, ["fullName", "acronym",
                                           "passingPeriodName", "schedules"], "v1.get_school_by_id"))


#
#
#   Error Handler Section
#
#

# override default rate limit exceeded error and return a JSON response instead
# https://flask-limiter.readthedocs.io/en/stable/#custom-rate-limit-exceeded-responses
@blueprint.errorhandler(429)
def ratelimit_handler(e):
    return make_response(
        jsonify(error="ratelimit exceeded %s" % e.description),
        429
    )


@blueprint.errorhandler(AuthError)
def handle_auth_error(ex):
    response = jsonify(ex.error)
    response.status_code = ex.status_code  # is text-based... this could be wrong
    return response


@blueprint.errorhandler(HTTPException)
def handle_HTTP_error(e):
    code = 500
    if isinstance(e, HTTPException):
        code = e.code
    return make_response(
        jsonify(error=str(code) + " " + e.name, message=e.description),
        404
    )
