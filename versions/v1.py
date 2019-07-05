import json
from os import environ as env

from flask import Blueprint, abort, jsonify
from werkzeug.exceptions import HTTPException
from flask_cors import cross_origin

import mysql.connector as mariadb
from bson import json_util
# from bson.objectid import ObjectId
import http.client

from helpers import requires_auth, check_scope, AuthError, Oops, id_to_uri, get_error_response, make_dict
from constants import APIScopes
#
# App Setup
#


DB_HOST = env.get("DB_HOST")
DB_USERNAME = env.get("DB_USERNAME")
DB_PASSWORD = env.get("DB_PASSWORD")

database = mariadb.connect(
    host=DB_HOST, user=DB_USERNAME, password=DB_PASSWORD, database='classclock')
cursor = database.cursor()

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

    cursor.execute(
        "SELECT HEX(school_id) as school_id, school_name, school_acronym FROM schools")

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

    try:
        school = schools.find_one({"_id": ObjectId(identifier)})
    except Exception:
        raise Oops("There was a problem retrieving the resource specified", 500)

    if school is None:
        raise Oops("No resource was found at the identifier specified", 404)

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
    print(e)
    return get_error_response(429, "ratelimit of " + e.description + " exceeded")


@blueprint.errorhandler(AuthError)
def handle_auth_error(e):
    return get_error_response(e.status_code, e.error)


@blueprint.errorhandler(Oops)
def handle_error(e):
    return get_error_response(e.status_code, e.message)


@blueprint.errorhandler(HTTPException)
def handle_HTTP_error(e):
    return get_error_response(e.code, e.description)


@blueprint.errorhandler(Exception)
def generic_exception_handler(e):
    # "We're sorry, but the electrons that were tasked with handling your request became terribly misguided and forgot what it is that they were supposed to be doing. Our team of scientists in the Electron Amnesia Recovery Ward is currently nursing them back to health; if you have any information about what it is these electrons were supposed to be doing at the time of this incident, please contact the maintainer of this service."
    print("an exception occurred")
    print(e)
    return get_error_response(500)
