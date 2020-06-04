import json
import uuid
import datetime
from flask_limiter import util
from flask import current_app
from os import environ as env

from flask import Blueprint, abort, jsonify, request
from werkzeug.exceptions import HTTPException
from flask_cors import CORS

# from bson import json_util
# from bson.objectid import ObjectId
import http.client
from common.db_schema import School as SchoolDB, db, BellSchedule as BellScheduleDB
from sqlalchemy import create_engine

from common.helpers import *
from common.constants import APIScopes
from common.schemas import SchoolSchema, BellScheduleSchema
from common.services import auth0management
import common.exceptions

#
# App Setup
#


DB_HOST = env.get("DB_HOST")
DB_USERNAME = env.get("DB_USERNAME")
DB_PASSWORD = env.get("DB_PASSWORD")


blueprint = Blueprint('v0', __name__)

CORS(blueprint, origins="https://web.classclock.app", allow_headers=[
    "Accept", "Authorization"])
    # supports_credentials=True)


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


@blueprint.route("/schools/", methods=['GET'])
@check_headers
def list_schools():
    """ Returns a list of schools
    ---
    responses:
      200:
        description: A list of schools
        schema:
          $ref: '#/definitions/School'
    """
    check_permissions([APIScopes.LIST_SCHOOLS])

    school_list = []
    schools = SchoolDB.query.all()

    for school in schools:
        school_list.append(school)
    return respond(response_data=SchoolSchema().dump(school_list, many=True))


@blueprint.route("/school/<string:school_id>/", methods=['GET'])
@check_headers
def get_school(school_id):
    """ Returns a single school
    ---
    responses:
      200:
        description: A single school object
        schema:
          $ref: '#/definitions/School'
    """
    check_permissions([APIScopes.LIST_SCHOOLS])

    school = SchoolDB.query.filter_by(id=school_id).first()
    #double check this
    if school is None:
        raise Oops("No school was found with the specified id.",
                    404, title="Resource Not Found")

    return respond(response_data=SchoolSchema().dump(school))


@blueprint.route("/school/", methods=['POST'])
@check_headers
@requires_auth
@requires_admin
def create_school(self):
    """ Creates a new school
    ---
    parameters:
      - name: school
        in: body
        type: object
        schema:
          $ref: '#/definitions/School'
    security:
      - ApiKeyAuth: []
    responses:
      200:
        description: A list of schools
        schema:
          $ref: '#/definitions/School'
    """

    check_permissions([APIScopes.CREATE_SCHOOL])
    # if len(list_owned_school_ids()) > 0:
    #     raise Oops(
    #         "Authorizing user is already the owner of another school", 401)

    data = get_request_body(request)
    
    new_object = SchoolDB(
        full_name=data['full_name'],
        alternate_freeperiod_name=data['alternate_freeperiod_name'],
        acronym=data['acronym'],
        owner_id=data['owner_id']
        )

    # if new_object.errors != {}:
    #     return handle_marshmallow_errors(new_object.errors)

    db.session.add(new_object)
    db.session.commit()

    #TODO: need to verify that the insert worked?

    return respond(response_data=SchoolSchema().dump(new_object)) #error checking


@blueprint.route("/school/<string:school_id>/", methods=['PATCH'])
@check_headers
@requires_auth
@requires_admin
def update_school(school_id):
    """
    updates a school
    ---
    security:
      - ApiKeyAuth: []
    
    """

    check_permissions([APIScopes.EDIT_SCHOOL])

    data = get_request_body(request)

    # if new_object.errors != {}:
    #     return handle_marshmallow_errors(new_object.errors)

    school = SchoolDB.query.filter_by(
        id=school_id, owner_id=get_api_user_id()).first()

    if school == None:
        raise Oops("No records were found. Please make sure you are the owner for the school you are trying to modify",
                    404, title="No Records Updated")

    if data.id.hex.lower() != school.id.lower():
        raise Oops("The id provided in the request body must match the id specified in the URL",
                    400, title="Identifier Mismatch")

    school.full_name = new_patch_val(data.full_name, school.full_name)
    school.acronym = new_patch_val(data.acronym, school.acronym)
    school.alternate_freeperiod_name = new_patch_val(
        data.alternate_freeperiod_name, school.alternate_freeperiod_name)
    # last_modified is automatically set in db_schema


    db.session.commit()
    #TODO: need to verify that the update worked?

    return respond(response_data=SchoolSchema().dump(school))


@blueprint.route("/school/<string:school_id>/", methods=['DELETE'])
@check_headers
@requires_auth
@requires_admin
def delete_school(school_id):
    """
    deletes a school
    ---
    security:
      - ApiKeyAuth: []

    """

    check_permissions(
        [APIScopes.DELETE_SCHOOL, APIScopes.DELETE_BELL_SCHEDULE])

    school = SchoolDB.query.filter_by(
        id=school_id, owner_id=get_api_user_id()).first()

    if school == None:
        raise Oops("No records were found. Please make sure you are the owner for the school you are trying to delete",
                    404, title="No Records Updated")
    
    db.session.delete(school)
    db.session.commit()
    # should this just archive the school? or delete it and all related records?
    # sqlalchemy can be set to cascade deletes (i think).
    return None, 204
    

# @blueprint.route("/school/<string:school_id>/bellschedules/", methods=['GET'])
# @check_headers
# def list_bellschedules(school_id):
#     check_permissions([APIScopes.LIST_BELL_SCHEDULES])

#     schedule_list = []
#     schedules = BellScheduleDB.query.filter_by(school_id=school_id)

#     for schedule in schedules:
#         schedule_list.append(schedule)
#     return BellScheduleSchema(exclude=('school_id',)).dump(schedule_list, many=True)


@blueprint.route("/bellschedule/<string:bell_schedule_id>/", methods=['GET'])
@check_headers
def get_bellschedule(bell_schedule_id):

    check_permissions([APIScopes.READ_BELL_SCHEDULE])

    schedule = BellScheduleDB.query.filter_by(
        id=bell_schedule_id).first()

    #double check this
    if schedule is None:
        raise Oops("No bell schedule was found with the specified id.",
                    404, title="Resource Not Found")

    return respond(response_data=BellScheduleSchema(exclude=('school_id',)).dump(schedule))


@blueprint.route("/bellschedule/", methods=['POST'])
@check_headers
@requires_auth
@requires_admin
def create_bellschedule():

    check_permissions([APIScopes.CREATE_BELL_SCHEDULE])

    # get school_id from a data parameter
    school = SchoolDB.query.filter_by(id=school_id).first()
    check_ownership(school)

    new_schedule = BellScheduleSchema().load(get_request_body(request)).data

    school.schedules.append(new_schedule)

    db.session.commit()

    return respond(response_data=BellScheduleSchema(exclude=('school_id',)).dump(new_schedule))


@blueprint.route("/bellschedule/<string:bell_schedule_id>", methods=['PATCH'])
@check_headers
@requires_auth
@requires_admin
def update_bellschedule(bell_schedule_id):

    check_permissions([APIScopes.EDIT_BELL_SCHEDULE])

    schedule = BellScheduleDB.query.filter_by(id=bell_schedule_id).first()
    school = SchoolDB.query.filter_by(id=schedule.school_id).first()
    check_ownership(school)

    updated_schedule = BellScheduleSchema().load(
        get_request_body(request)).data

# no need to check for this. just overwrite the id value with the url-provided one
    # if not updated_schedule.id or updated_schedule.id.lower() != bell_schedule_id.lower():
    #     raise Oops("The identifier provided in the request body must match the identifier specified in the URL",
    #                 400, title="Identifier Mismatch")

    schedule.name = new_patch_val(updated_schedule.name, schedule.name)
    schedule.display_name = new_patch_val(
        updated_schedule.display_name, schedule.display_name)
                            
    db.session.commit()

    return respond(response_data=BellScheduleSchema(exclude=('school_id',)).dump(schedule))


@blueprint.route("/bellschedule/<string:bell_schedule_id>", methods=['DELETE'])
@check_headers
@requires_auth
@requires_admin
def delete_bellschedule(bell_schedule_id):

    check_permissions([APIScopes.DELETE_BELL_SCHEDULE])

    schedule = BellScheduleDB.query.filter_by(id=bell_schedule_id).first()
    school = SchoolDB.query.filter_by(id=schedule.school_id).first()
    check_ownership(school)

    db.session.delete(schedule)

    return None, 204

#
# Routes
#


# register_api(api, School, "v0", name_of_optional_param="school_id")

# register_api(api, BellSchedule, "v0", url_prefix="/school/<string:school_id>",
#              name_of_optional_param="bell_schedule_id")



@blueprint.before_request
def before():
    current_app.logger.info( "Handling " + request.method + " Request for endpoint " +  request.path + " from API user '" + get_api_user_id() + "' from address " + util.get_remote_address() )
    pass    


@blueprint.after_request
def after_request(response):
    response.headers['Content-Type'] = 'application/json'
    return response

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
    return respond(
        make_error_object(429, title="Ratelimit Exceeded",
                                  message="ratelimit of " + e.description + " exceeded"),
        code=429
    )


@blueprint.errorhandler(AuthError)
def handle_auth_error(e):
    return respond(
        make_error_object(e.status_code, message=e.error), code=e.status_code
    )


@blueprint.errorhandler(Oops)
def handle_error(e):
    if e.title is not None:
        return respond(
            make_error_object(e.status_code, message=e.message, title=e.title), code=e.status_code
        )
    else:
        return respond(
            make_error_object(e.status_code, message=e.message), code=e.status_code
        )


@blueprint.errorhandler(HTTPException)
def handle_HTTP_error(e):
    return respond(
        make_error_object(
            e.code, title=e.name(), message=e.description),
        code=e.code
    )


# @blueprint.errorhandler(Exception)
# def generic_exception_handler(e):
#     # "We're sorry, but the electrons that were tasked with handling your request became terribly misguided and forgot what it is that they were supposed to be doing. Our team of scientists in the Electron Amnesia Recovery Ward is currently nursing them back to health; if you have any information about what it is these electrons were supposed to be doing at the time of this incident, please contact the maintainer of this service."
#     print("an exception occurred")
#     print(e)
#     return respond(
#         make_error_object(500), code=500, headers={'Content-Type': 'application/json'}
#     )
