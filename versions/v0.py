import json
from os import environ as env

from flask import Blueprint, abort, jsonify, request
from flask_restful import Api, Resource
from werkzeug.exceptions import HTTPException
from flask_cors import cross_origin

import mysql.connector as mariadb
from bson import json_util
# from bson.objectid import ObjectId
import http.client

from common.helpers import requires_auth, check_scope, AuthError, Oops, make_dict, make_jsonapi_response, make_jsonapi_resource_object, make_jsonapi_error_object, register_api, check_headers, deconstruct_resource_object, get_column_update_SQL
from common.constants import APIScopes
from common.schemas import SchoolSchema

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
api = Api(blueprint, decorators=[requires_auth, check_headers])


@api.representation('application/vnd.api+json')
def output_json(data, code, headers={}):
    return make_jsonapi_response(response_data=data, code=code, headers=headers)

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

class School(Resource):

    # for identifiers in the response, keys_uri_map specifies the function that would be needed to request the resource that the ID points to (so if the id is a schedule id, this would map to the name of the schedule function). this is used for generating URI's in responses
    keys_uri_map = {"id": "v0.single_school"}

    def get(self, school_id):
        if school_id is None:
            school_list = []
            summary_schema = SchoolSchema(
                only=('identifier', 'full_name', 'acronym'))

            cursor.execute(
                "SELECT HEX(school_id) as school_id, school_name, school_acronym FROM schools")
            # dict_keys_map defines the keys for the dictionary that is generated from the tuples returned from the database (so order matters)
            dict_keys_map = ("id", "full_name", "acronym")

            for school in cursor:
                result = summary_schema.load(make_dict(school, dict_keys_map))

                print(result.data)
                school_uri = api.url_for(
                    type(self), school_id=result.data.identifier, _external=True)

                school_list.append(
                    make_jsonapi_resource_object(
                        result.data, SchoolSchema(
                            only=('full_name', 'acronym')), school_uri)
                )

            return school_list

        else:

            detail_schema = SchoolSchema(
                only=('identifier', 'full_name', 'acronym', 'alternate_freeperiod_name', 'creation_date'))
            # .format(self.db_scan_table)
            sql = ('SELECT HEX(school_id) as school_id, school_name, school_acronym, alternate_freeperiod_name, creation_date FROM schools WHERE school_id= UNHEX(%s)')

            cursor.execute(sql, (school_id,))

            # dict_keys_map defines the keys for the dictionary that is generated from the tuples returned from the database (so order matters)
            dict_keys_map = ("id", "full_name", "acronym",
                             "alternate_freeperiod_name", "creation_date")

            fetch = cursor.fetchone()

            if fetch is None:
                return make_jsonapi_error_object(404, title="Resource Not Found", message="No school was found with the specified id."), 404

            # print(fetch)
            result = detail_schema.load(make_dict(fetch, dict_keys_map))
            uri = api.url_for(
                type(self), school_id=result.data.identifier, _external=True)

            return make_jsonapi_resource_object(result.data, SchoolSchema(only=('full_name', 'acronym', 'alternate_freeperiod_name', 'creation_date')), uri)

    def patch(self, school_id):
        """ input:
        {
            "data": {
                "type": "school",
                "id": "2C49E3159EE011E986F2181DEA92AD79",
                "links": {
                    "self": "http://localhost:5000/v0/school/2C49E3159EE011E986F2181DEA92AD79"
                },
                "attributes": {
                    "acronym": "LMHS",
                    "creation_date": "2019-07-04T21:48:46+00:00",
                    "alternate_freeperiod_name": null,
                    "full_name": "Lake Mosswego High School"
                }
            }
        }
        """

        schema = SchoolSchema()
        data = request.get_json()
        new_object = schema.load(deconstruct_resource_object(data["data"]))

        if new_object.errors != {}:
            error_list = []
            for field in new_object.errors:
                error = make_jsonapi_error_object(
                    400, title="Request body validation failure", message=new_object.errors[field])
                error_list.append(error)
            return error_list, 400

        if new_object.data.identifier != school_id:
            return make_jsonapi_error_object(
                400, title="Identifier Mismatch", message="The identifier provided in the request body must match the identifier specified in the URL"), 400

        # build SQL command

        sql_columns, values = get_column_update_SQL(
            new_object.data, SchoolSchema(only=('full_name', 'acronym', 'alternate_freeperiod_name')), {"acronym": "school_acronym", "full_name": "school_name"})

        values += (school_id,)

        # get existing school matching the ID in the request
        # replace all contents of the school (besides the id and maybe creation date) with the contents from the request (if we're certain that theyre valid)
        # UPDATE table_name SET column1 = value1, column2 = value2, ... WHERE condition;
        sql = ('UPDATE schools SET ' + sql_columns +
               ' WHERE school_id= UNHEX(%s)')

        cursor.execute(sql, values)
        database.commit()

        return schema.dump(new_object.data).data

    def delete(self):
        pass


#
# Routes
#


register_api(api, School, param_name="school_id", param_type="string")


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
    return make_jsonapi_response(
        make_jsonapi_error_object(429, title="Ratelimit Exceeded",
                                  message="ratelimit of " + e.description + " exceeded"),
        code=429
    )


@blueprint.errorhandler(AuthError)
def handle_auth_error(e):
    return make_jsonapi_response(
        make_jsonapi_error_object(e.status_code, message=e.error), code=e.status_code
    )


@blueprint.errorhandler(Oops)
def handle_error(e):
    return make_jsonapi_response(
        make_jsonapi_error_object(e.status_code, message=e.message), code=e.status_code
    )


@blueprint.errorhandler(HTTPException)
def handle_HTTP_error(e):
    return make_jsonapi_response(
        make_jsonapi_error_object(
            e.code, title=e.name(), message=e.description),
        code=e.code
    )


@blueprint.errorhandler(Exception)
def generic_exception_handler(e):
    # "We're sorry, but the electrons that were tasked with handling your request became terribly misguided and forgot what it is that they were supposed to be doing. Our team of scientists in the Electron Amnesia Recovery Ward is currently nursing them back to health; if you have any information about what it is these electrons were supposed to be doing at the time of this incident, please contact the maintainer of this service."
    print("an exception occurred")
    print(e)
    return make_jsonapi_response(
        make_jsonapi_error_object(500)
    )
