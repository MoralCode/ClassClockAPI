import json
import uuid
import datetime
from os import environ as env

from flask import Blueprint, abort, jsonify, request
from flask_restful import Api, Resource
from werkzeug.exceptions import HTTPException
from flask_cors import cross_origin

import mysql.connector as mariadb
# from bson import json_util
# from bson.objectid import ObjectId
import http.client

from common.helpers import requires_auth, check_scope, AuthError, Oops, make_dict, make_jsonapi_response, make_jsonapi_resource_object, make_jsonapi_error_object, register_api, check_headers, deconstruct_resource_object, build_sql_column_update_list, handle_marshmallow_errors, time_from_delta
from common.constants import APIScopes
from common.schemas import SchoolSchema, BellScheduleSchema, ClassPeriodSchema

#
# App Setup
#


DB_HOST = env.get("DB_HOST")
DB_USERNAME = env.get("DB_USERNAME")
DB_PASSWORD = env.get("DB_PASSWORD")

database = mariadb.connect(
    host=DB_HOST, user=DB_USERNAME, password=DB_PASSWORD, database='classclock')
cursor = database.cursor()


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
                raise Oops("No school was found with the specified id.",
                           404, title="Resource Not Found")

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
            raise Oops("The identifier provided in the request body must match the identifier specified in the URL",
                       400, title="Identifier Mismatch")
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

    def get(self, school_id, bell_schedule_id):
        if bell_schedule_id is None:
            bell_schedule_list = []

            cursor.execute(
                "SELECT HEX(bell_schedule_id) as bell_schedule_id, bell_schedule_name, bell_schedule_display_name FROM bellschedules WHERE school_id=%s", (uuid.UUID(school_id).bytes,))
            # dict_keys_map defines the keys for the dictionary that is generated from the tuples returned from the database (so order matters)
            dict_keys_map = ("id", "full_name", "display_name")

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

        else:

            cursor.execute(
                'SELECT bell_schedule_name, bell_schedule_display_name, creation_date, last_modified FROM bellschedules WHERE bell_schedule_id=%s',
                (uuid.UUID(bell_schedule_id).bytes, )
            )

            requested_bell_schedule = cursor.fetchone()

            if not requested_bell_schedule:
                raise Oops("No bell schedule was found with the specified id.",
                           404, title="Resource Not Found")

            cursor.execute(
                'SELECT date FROM bellscheduledates WHERE bell_schedule_id=%s',
                (uuid.UUID(bell_schedule_id).bytes, )
            )
            dates = cursor.fetchall()
            if not dates:
                dates = []

            cursor.execute(
                'SELECT classperiod_name, start_time, end_time, creation_date FROM bellschedulemeetingtimes WHERE bell_schedule_id=%s',
                (uuid.UUID(bell_schedule_id).bytes, )
            )
            meeting_times = cursor.fetchall()
            if not meeting_times:
                meeting_times = []

            # key maps define the keys for the dictionary that is generated from the tuples returned from the database (so order matters)
            schedule_keys_map = ("full_name", "display_name",
                                 "creation_date", "last_modified")
            meetingtime_keys_map = (
                "name", "start_time", "end_time", "creation_date")

            return_data = make_dict(requested_bell_schedule, schedule_keys_map)
            return_data["id"] = uuid.UUID(bell_schedule_id)
            return_data["school_id"] = uuid.UUID(school_id)
            return_data["creation_date"] = return_data["creation_date"].isoformat()
            # extract list of dates from list of tuples of dates
            return_data["dates"] = [date[0].isoformat() for date in dates]

            # convert timedeltas to times
            classes = []

            for meeting_time in meeting_times:
                values = []
                for value in meeting_time:
                    if isinstance(value, datetime.timedelta):
                        values.append(time_from_delta(value))
                    elif isinstance(value, datetime.datetime):
                        values.append(value.isoformat())
                    else:
                        values.append(value)

                classes.append(values)

            meeting_times = [make_dict(meetingtime, meetingtime_keys_map)
                             for meetingtime in classes]

            return_data["meeting_times"] = meeting_times

            result, errors = BellScheduleSchema().load(return_data)

            if errors != {}:
                return handle_marshmallow_errors(errors)

            return make_jsonapi_resource_object(result, BellScheduleSchema(exclude=('type', 'identifier', 'school_id')), "v0")

    def post(self, school_id):

        # also need to be able to process bell schedule days and bell schedule meeting times as input from request to update the database

        schema = BellScheduleSchema()
        data = deconstruct_resource_object(request.get_json()["data"])
        data["school_id"] = uuid.UUID(school_id)
        new_object = schema.load(data)

        if new_object.errors != {}:
            return handle_marshmallow_errors(new_object.errors)

        # print(new_object)

        # build SQL command
        cursor.execute(
            "INSERT INTO bellschedules (bell_schedule_id, bell_schedule_name, bell_schedule_display_name, school_id, creation_date, last_modified) VALUES (%s, %s, %s, %s, NOW(), NOW())",
            (new_object.data.identifier.bytes, new_object.data.full_name,
             new_object.data.display_name, new_object.data.school_id.bytes)
        )

        dates_to_add = []

        for date in new_object.data.dates:
            dates_to_add.append(
                (new_object.data.identifier.bytes,
                 new_object.data.school_id.bytes,
                 date)
            )

        dates_sql = "INSERT INTO bellscheduledates (bell_schedule_id, school_id, date, creation_date) VALUES (%s, %s, %s, NOW())"

        try:
            cursor.executemany(dates_sql, dates_to_add)
            database.commit()
        except:
            database.rollback()

        meeting_times_to_add = []

        for meeting_time in new_object.data.meeting_times:
            meeting_times_to_add.append(
                (new_object.data.identifier.bytes,
                 new_object.data.school_id.bytes,
                 meeting_time.name,
                 meeting_time.start_time,
                 meeting_time.end_time)
            )

        meeting_times_sql = "INSERT INTO bellschedulemeetingtimes (bell_schedule_id, school_id, classperiod_name, start_time, end_time, creation_date) VALUES (%s, %s, %s, %s, %s, NOW())"

        try:
            cursor.executemany(meeting_times_sql, meeting_times_to_add)
            database.commit()
        except:
            database.rollback()

        return make_jsonapi_resource_object(new_object.data, BellScheduleSchema(exclude=('type', 'identifier', 'school_id')), "v0")

    def delete(self, school_id, bell_schedule_id):

        # need to delete the whole bell schedule (meeting times and days too)
        # DELETE FROM bellschedules, bellscheduledates, bellschedulemeetingtimes WHERE bell_schedule_id=%s AND school_id=%s
        schedule_delete = (
            'DELETE FROM bellschedules WHERE bell_schedule_id=%s')
        days_delete = (
            'DELETE FROM bellscheduledates WHERE bell_schedule_id=%s')
        meeting_times_delete = (
            'DELETE FROM bellschedulemeetingtimes WHERE bell_schedule_id=%s')

        try:

            cursor.execute(days_delete, (uuid.UUID(bell_schedule_id).bytes,))
            cursor.execute(meeting_times_delete,
                           (uuid.UUID(bell_schedule_id).bytes,))
            cursor.execute(schedule_delete,
                           (uuid.UUID(bell_schedule_id).bytes,))

            database.commit()
        except Exception as e:
            print(e)
            database.rollback()

        return None, 204


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
    if e.title is not None:
        return make_jsonapi_response(
            make_jsonapi_error_object(e.status_code, message=e.message, title=e.title), code=e.status_code
        )
    else:
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
