import json
from os import environ as env
from common.helpers import AuthenticatedResource

from flask import Blueprint, abort, jsonify
from flask_restful import Api
from werkzeug.exceptions import HTTPException
from flask_cors import cross_origin

import mysql.connector as mariadb
from bson import json_util
# from bson.objectid import ObjectId
import http.client

from common.helpers import requires_auth, check_scope, AuthError, Oops, make_dict, make_jsonapi_response, make_jsonapi_resource_object, make_jsonapi_error_object
from common.constants import APIScopes
#
# App Setup
#


DB_HOST = env.get("DB_HOST")
DB_USERNAME = env.get("DB_USERNAME")
DB_PASSWORD = env.get("DB_PASSWORD")

database = mariadb.connect(
    host=DB_HOST, user=DB_USERNAME, password=DB_PASSWORD, database='classclock')
cursor = database.cursor(prepared=True)


blueprint = Blueprint('v0', __name__)
api = Api(blueprint)


# @blueprint.route("/schools", methods=['GET'])
# @cross_origin(headers=["Content-Type", "Authorization"])
# @cross_origin(headers=["Access-Control-Allow-Origin", "http://localhost:5000"])
# @requires_auth
# def get_schools():
#     """Get a list of every publicly accessible ClassClock school
#     ---
#     responses:
#         '200':
#             description: A list of every publicly accessible ClassClock school
#         '400':
#             description: Unauthorized for some reason such as an invalid access token or incorrect scopes
#     """


# @blueprint.route("/school/<string:identifier>", methods=['GET'])
# @cross_origin(headers=["Content-Type", "Authorization"])
# @cross_origin(headers=["Access-Control-Allow-Origin", "http://localhost:5000"])
# @requires_auth
# def get_school_by_id(identifier):
#     """
#     Get information about a single school
#     ---
#     parameters:
#     - name: identifier
#       in: path
#       type: string
#       required: true
#       description: the hexadecimal identifier of the school you are requesting
#     responses:
#         200:
#             description: data for a single school
#         '400':
#             description: Unauthorized for some reason such as an invalid access token or incorrect scopes
#         default:
#             description: error payload

#     """

class School(AuthenticatedResource):
    def get(self, identifier):
        if identifier is None:
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

            return make_jsonapi_response(response_object=make_jsonapi_resource_object(schools_list, "school", keys_uri_map))

        else:

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
                return make_jsonapi_response(response_object=make_jsonapi_error_object(404, title="Resource Not Found", message="No school was found with the specified id."))

            return make_jsonapi_response(response_object=make_jsonapi_resource_object(make_dict(fetch, dict_keys_map), "school", keys_uri_map))

    def put(self):
        pass

    def delete(self):
        pass


def register_api(resource, endpoint, url, pk='id', pk_type='int'):
    view_func = resource.as_view(endpoint)
    api.add_resource(resource, defaults={
                     pk: None}, view_func=view_func, endpoint=endpoint, methods=['GET', ])
    api.add_resource(resource, view_func=view_func,
                     endpoint=endpoint, methods=['POST', ])
    api.add_resource('%s<%s:%s>' % (url, pk_type, pk), view_func=view_func,
                     endpoint=endpoint, methods=['GET', 'PUT', 'DELETE'])


#
# Routes
#

register_api(School, "/school/", "school", pk="school_id", pk_type="string")
# register_api(UserAPI, 'user_api', '/users/', pk='user_id')
# api.add_resource(School, '/school/<string:identifier>')
# api.add_resource(HelloWorld, '/', '/hello')
# api.add_resource(HelloWorld, '/', '/hello')
# api.add_resource(HelloWorld, '/', '/hello')
# api.add_resource(HelloWorld, '/', '/hello')


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
