import json
from os import environ as env

from flask import Blueprint, abort, jsonify
from werkzeug.exceptions import HTTPException
from flask_cors import cross_origin

import mysql.connector as mariadb
from bson import json_util
# from bson.objectid import ObjectId
import http.client

from helpers import requires_auth, check_scope, AuthError, Oops, make_jsonapi_error_response, make_dict, make_jsonapi_success_response
from constants import APIScopes
#
# App Setup
#


DB_HOST = env.get("DB_HOST")
DB_USERNAME = env.get("DB_USERNAME")
DB_PASSWORD = env.get("DB_PASSWORD")

database = mariadb.connect(
    host=DB_HOST, user=DB_USERNAME, password=DB_PASSWORD, database='classclock')
cursor = database.cursor(prepared=True)

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

    schools_list = []

    cursor.execute(
        "SELECT HEX(school_id) as school_id, school_name, school_acronym FROM schools")
    # dict_keys_map defines the keys for the dictionary that is generated from the tuples returned from the database (so order matters)
    dict_keys_map = ("id", "fullName", "acronym")

    # for identifiers in the response, keys_uri_map specifies the function that would be needed to request the resource that the ID points to (so if the id is a schedule id, this would map to the name of the schedule function). this is used for generating URI's in responses
    keys_uri_map = {"id": "v1.get_school_by_id"}

    for school in cursor:
        schools_list.append(make_dict(
            school, dict_keys_map)
        )

    return make_jsonapi_success_response(schools_list, "school", keys_uri_map)


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
      description: the hexadecimal identifier of the school you are requesting
    responses:
        200:
            description: data for a single school
        '400':
            description: Unauthorized for some reason such as an invalid access token or incorrect scopes
        default:
            description: error payload

    """

    # .format(self.db_scan_table)
    sql = ('SELECT HEX(school_id) as school_id, school_name, school_acronym, alternate_freeperiod_name, creation_date FROM schools WHERE school_id= UNHEX(%s)')

    cursor.execute(sql, (identifier,))

    # dict_keys_map defines the keys for the dictionary that is generated from the tuples returned from the database (so order matters)
    dict_keys_map = ("id", "fullName", "acronym",
                     "alternate_freeperiod_name", "creation_date")

    # for identifiers in the response, keys_uri_map specifies the function that would be needed to request the resource that the ID points to (so if the id is a schedule id, this would map to the name of the schedule function). this is used for generating URI's in responses
    keys_uri_map = {"id": "v1.get_school_by_id"}

    # for value in cursor:
    #     print(value)

    fetch = cursor.fetchone()

    if fetch is None:
        return make_jsonapi_error_response(404, title="Resource Not Found", message="No school was found with the specified id.")

    return make_jsonapi_success_response(make_dict(fetch, dict_keys_map), "school", keys_uri_map)

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
    return make_jsonapi_error_response(429, title="Ratelimit Exceeded", message="ratelimit of " + e.description + " exceeded")


@blueprint.errorhandler(AuthError)
def handle_auth_error(e):
    return make_jsonapi_error_response(e.status_code, message=e.error)


@blueprint.errorhandler(Oops)
def handle_error(e):
    return make_jsonapi_error_response(e.status_code, message=e.message)


@blueprint.errorhandler(HTTPException)
def handle_HTTP_error(e):
    return make_jsonapi_error_response(e.code, message=e.description)


@blueprint.errorhandler(Exception)
def generic_exception_handler(e):
    # "We're sorry, but the electrons that were tasked with handling your request became terribly misguided and forgot what it is that they were supposed to be doing. Our team of scientists in the Electron Amnesia Recovery Ward is currently nursing them back to health; if you have any information about what it is these electrons were supposed to be doing at the time of this incident, please contact the maintainer of this service."
    print("an exception occurred")
    print(e)
    return make_jsonapi_error_response(500)
