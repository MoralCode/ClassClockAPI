import json
import uuid
from os import environ as env

from flask import Blueprint, abort, jsonify, request
from flask_restful import Api, Resource
from werkzeug.exceptions import HTTPException
from flask_cors import cross_origin

import mysql.connector as mariadb
# from bson import json_util
# from bson.objectid import ObjectId
import http.client

from common.helpers import requires_auth, check_scope, AuthError, Oops, make_dict, make_jsonapi_response, make_jsonapi_resource_object, make_jsonapi_error_object, register_api, check_headers, deconstruct_resource_object, build_sql_column_update_list, handle_marshmallow_errors
from common.constants import APIScopes
from common.schemas import SchoolSchema, BellScheduleSchema

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

                school_list.append(
                    make_jsonapi_resource_object(
                        result.data, SchoolSchema(
                            only=('full_name', 'acronym')), "v0")
                )

            return school_list

        else:

            detail_schema = SchoolSchema(
                only=('identifier', 'full_name', 'acronym', 'alternate_freeperiod_name', 'creation_date'))
            # .format(self.db_scan_table)
            sql = ('SELECT HEX(school_id) as school_id, school_name, school_acronym, alternate_freeperiod_name, creation_date FROM schools WHERE school_id=%s')

            cursor.execute(sql, (uuid.UUID(school_id).bytes,))

            # dict_keys_map defines the keys for the dictionary that is generated from the tuples returned from the database (so order matters)
            dict_keys_map = ("id", "full_name", "acronym",
                             "alternate_freeperiod_name", "creation_date")

            fetch = cursor.fetchone()

            if fetch is None:
                return make_jsonapi_error_object(404, title="Resource Not Found", message="No school was found with the specified id."), 404

            # print(fetch)
            result = detail_schema.load(make_dict(fetch, dict_keys_map))

            return make_jsonapi_resource_object(result.data, SchoolSchema(exclude=('type', 'identifier')), "v0")

    def post(self):

        schema = SchoolSchema()
        data = request.get_json()
        new_object = schema.load(deconstruct_resource_object(data["data"]))

        if new_object.errors != {}:
            return handle_marshmallow_errors(new_object.errors)

        # build SQL command
        # INSERT INTO schools (last_modified, school_name, creation_date, alternate_freeperiod_name, school_acronym, school_id) VALUES (%s, %s, %s, %s, %s, %s)
        '''
        Needs custom mysql command:
        school_id
        last_modified
        creation_date - determeined by if its new or not


        '''

        # print(vars(new_object.data))
        # sql, sql_values = build_sql_column_insert_list(
        #     new_object.data, SchoolSchema(), {"id": "school_id", "acronym": "school_acronym", "full_name": "school_name"}, "schools")

        sql = ("INSERT INTO schools (school_id, school_name, school_acronym, alternate_freeperiod_name, last_modified, creation_date) VALUES (%s, %s, %s, %s, NOW(), NOW())")

        sql_values = (new_object.data.identifier.bytes, new_object.data.full_name,
                      new_object.data.acronym, new_object.data.alternate_freeperiod_name)
        cursor.execute(sql, sql_values)
        database.commit()

        # print(cursor.lastrowid)
        # print(vars(cursor))
        # # print()
        # # print(vars(connection))
        # new_object.data.identifier = cursor.lastrowid

        # cursor.lastrowid TO GET THTE ID OF THE LAST ROW INSERTED

        return make_jsonapi_resource_object(new_object.data, SchoolSchema(exclude=('type', 'identifier')), "v0")

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
            return handle_marshmallow_errors(new_object.errors)

        if new_object.data.identifier.hex != school_id.lower():
            return make_jsonapi_error_object(
                400, title="Identifier Mismatch", message="The identifier provided in the request body must match the identifier specified in the URL"), 400

        # build SQL command

        values = ()
        sql = 'UPDATE schools SET '

        if new_object.data.full_name is not None:
            sql += "school_name=%s, "
            values += (new_object.data.full_name,)

        if new_object.data.acronym is not None:
            sql += "school_acronym=%s, "
            values += (new_object.data.acronym,)

        if new_object.data.alternate_freeperiod_name is not None:
            sql += "alternate_freeperiod_name=%s, "
            values += (new_object.data.alternate_freeperiod_name,)

        sql += "last_modified=NOW() "
        sql += 'WHERE school_id=%s'

        values += (uuid.UUID(school_id).bytes,)

        cursor.execute(sql, values)
        database.commit()

        return make_jsonapi_resource_object(new_object.data, SchoolSchema(exclude=('type', 'identifier')), "v0")

    def delete(self, school_id):
        sql = ('DELETE FROM schools WHERE school_id=%s')

        cursor.execute(sql, (uuid.UUID(school_id).bytes,))
        database.commit()

        # should this just archive the school? or delete it and all related records?
        # just remembered it can auto-cascade because foreign keys
        # operation = 'SELECT 1; INSERT INTO t1 VALUES (); SELECT 2'
        # cursor.execute(operation, multi=True):
        return None, 204


class BellSchedule(Resource):

    table_name = "bellschedules"

    def get(self, school_id, bell_schedule_id):
        if bell_schedule_id is None:
            bell_schedule_list = []

            cursor.execute("SELECT HEX(bell_schedule_id) as bell_schedule_id, bell_schedule_name FROM " +
                           self.table_name + " WHERE school_id=%s", (uuid.UUID(school_id).bytes,))
            # dict_keys_map defines the keys for the dictionary that is generated from the tuples returned from the database (so order matters)
            dict_keys_map = ("id", "full_name")

            for bell_schedule in cursor:

                data = make_dict(bell_schedule, dict_keys_map)
                data["school_id"] = uuid.UUID(school_id)
                # print(data)
                result, errors = BellScheduleSchema().load(data)
                # print(errors)
                if errors != {}:
                    return handle_marshmallow_errors(errors)
                # print(result)
                # # print(type(result))

                bell_schedule_list.append(
                    make_jsonapi_resource_object(
                        result, BellScheduleSchema(only=('full_name', 'display_name')), "v0")
                )

            return bell_schedule_list

#
# Routes
#


register_api(api, School, "v0", name_of_optional_param="school_id")

register_api(api, BellSchedule, "v0", url_prefix="/school/<string:school_id>",
             name_of_optional_param="bell_schedule_id")


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
