import uuid
import datetime
from flask_limiter import util
from flask import current_app, json
from os import environ as env

from flask import Blueprint, abort, jsonify, request
from werkzeug.exceptions import HTTPException
from flask_cors import CORS
from marshmallow.exceptions import ValidationError

# from bson import json_util
# from bson.objectid import ObjectId
import http.client
from common.db_schema import School as SchoolDB, db, BellSchedule as BellScheduleDB
from sqlalchemy import create_engine

from common.helpers import *
from common.constants import APIScopes, HTTP_DATE_FORMAT
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

flex_url = "http://localhost:3000" if env.get("FLASK_ENV") == 'development' else "classclock-*-moralcode.vercel.app"


CORS(blueprint, origins=["https://web.classclock.app", "https://beta.web.classclock.app", flex_url], allow_headers=[
    "Accept", "Authorization", "Content-Type"])
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
#             content:
#               application/json:
#                   ...
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

@blueprint.route("/ping", strict_slashes=False, methods=['GET'])
def ping():
    """ Returns the text "pong" as a connectivity check
    ---
    responses:
      200:
        description: the text "pong"
    """
    return "pong"

# TODO: add a search parameter
@blueprint.route("/schools", strict_slashes=False, methods=['GET'])
@check_headers
def list_schools():
    """ Returns a list of schools
    ---
    responses:
      200:
        description: A list of schools
        content:
            application/json:
                schema:
                    $ref: '#/definitions/School'
    """

    school_list = []
    schools = SchoolDB.query.filter_by(soft_deleted=False).all()

    return respond(SchoolSchema(exclude=('soft_deleted',)).dump(schools, many=True))


@blueprint.route("/school/<string:school_id>", strict_slashes=False, methods=['GET'])
@check_headers
def get_school(school_id):
    """ Returns a single school
    ---
    responses:
      200:
        description: A single school object
        schema:
          $ref: '#/definitions/School'
    parameters:
        - in: path
          name: school_id
          schema:
            type: string
            length: 32
          required: true
        - in: header
          name: If-Modified-Since
          schema:
            type: string
            format: date
          required: false
    """

    school = SchoolDB.query.filter_by(id=school_id, soft_deleted=False).first()
    #double check this
    if school is None:
        raise Oops("No school was found with the specified id.",
                    404, title="Resource Not Found")

    if 'If-Modified-Since' in request.headers:
        since = datetime.strptime(request.headers.get('If-Modified-Since'), HTTP_DATE_FORMAT)
        # TODO: make this a more robust check
        if school.last_modified == since:
            return respond(code=304) #Not Modified

    return respond(SchoolSchema(exclude=('soft_deleted',)).dump(school))


@blueprint.route("/school", strict_slashes=False, methods=['POST'])
@check_headers
@requires_auth(permissions=[APIScopes.CREATE_SCHOOL])
@requires_admin
def create_school():
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
    # if len(list_owned_school_ids()) > 0:
    #     raise Oops(
    #         "Authorizing user is already the owner of another school", 401)

    data = get_request_body(request)
    
    if data is None:
        raise Oops("Invalid or non-JSON request body provided.", 400)

    new_object = None 
    try:
        #Numbers, booleans, strings, and ``None`` are considered invalid input to `Schema.load
        new_object = SchoolSchema().load(data, session=db.session)
    except ValidationError as err:
        # print(err.messages)  # => {"email": ['"foo" is not a valid email address.']}
        # print(err.valid_data)
        return respond(err.messages, code=400)

    # if new_object.errors != {}:
    #     return handle_marshmallow_errors(new_object.errors)

    db.session.add(new_object)
    db.session.commit()

    #TODO: need to verify that the insert worked?

    return respond(SchoolSchema(exclude=('soft_deleted',)).dump(new_object))


@blueprint.route("/school/<string:school_id>", strict_slashes=False, methods=['PATCH'])
@check_headers
@requires_auth(permissions=[APIScopes.EDIT_SCHOOL])
@requires_admin
def update_school(school_id):
    """
    updates a school
    ---
    security:
      - ApiKeyAuth: []
    parameters:
        - in: path
          name: school_id
          schema:
            type: string
            length: 32
          required: true
        - in: body
          name: school
          schema:
            $ref: '#/definitions/School'
          required: true
    """

    data = get_request_body(request)

    # if new_object.errors != {}:
    #     return handle_marshmallow_errors(new_object.errors)

    school = SchoolDB.query.filter_by(id=school_id, soft_deleted=False).first()

    if school is None:
        raise Oops("No records could be updated because none were found",
                    404, title="No Records Found")
    else:
        check_ownership(school)
        

     # check modification times
     # this needs to happen after the school is retreived from the DB for comparison
    if 'If-Unmodified-Since' in request.headers:
        since = datetime.datetime.strptime(request.headers.get('If-Unmodified-Since'), HTTP_DATE_FORMAT)
        trap_object_modified_since(school.last_modified, since)


    try:
        updated_school = SchoolSchema().load(data, session=db.session, instance=school)
    except ValidationError as err:
        # print(err.messages)  # => {"email": ['"foo" is not a valid email address.']}
        # print(err.valid_data)
        return respond(err.messages, code=400)

    db.session.commit()
    #TODO: need to verify that the update worked?

    return respond(SchoolSchema(exclude=('soft_deleted',)).dump(school))


@blueprint.route("/school/<string:school_id>", strict_slashes=False, methods=['DELETE'])
@check_headers
@requires_auth(permissions=[APIScopes.DELETE_SCHOOL, APIScopes.DELETE_BELL_SCHEDULE])
@requires_admin
def delete_school(school_id):
    """
    deletes a school
    ---
    security:
      - ApiKeyAuth: []
    parameters:
        - in: path
          name: school_id
          schema:
            type: string
            length: 32
          required: true
        - in: header
          name: If-Unmodified-Since
          schema:
            type: string
            format: date
          required: false

    """

    school = SchoolDB.query.filter_by(id=school_id, soft_deleted=False).first()
    if school is None:
        raise Oops("No records could be deleted because none were found",
                    404, title="No Records Found")
    else:
        check_ownership(school)

    # check modification times
    # this needs to happen after the school is retreived from the DB for comparison
    if 'If-Unmodified-Since' in request.headers:
        since = datetime.datetime.strptime(request.headers.get('If-Unmodified-Since'), HTTP_DATE_FORMAT)
        trap_object_modified_since(school.last_modified, since)
    
    db.session.delete(school)
    db.session.commit()
    # should this just archive the school? or delete it and all related records?
    # sqlalchemy can be set to cascade deletes (i think).
    return None, 204

@blueprint.route("/bellschedules", strict_slashes=False, methods=['GET'])
@check_headers
@requires_auth#(permissions=[APIScopes.DELETE_SCHOOL, APIScopes.DELETE_BELL_SCHEDULE])
@requires_admin
def list_owned_bellschedules():
    """
    gets a list of bell schedules that are part of schools that the current user owns
    ---
    security:
      - ApiKeyAuth: []
    responses:
      200:
        description: A list of bell schedules 
        schema:
          $ref: '#/definitions/BellSchedule'
    """
    #if get_api_user_id() not in school.owner_id

    schedules = BellScheduleDB.query.join(BellScheduleDB.school).filter(SchoolDB.owner_id==get_api_user_id(), SchoolDB.soft_deleted==False, BellScheduleDB.soft_deleted==False)

    return respond(BellScheduleSchema(exclude=('school_id','soft_deleted')).dump(schedules, many=True))
    
#TODO: add filtering for return values to reduce size of response. i.e. filter dates by after today, exclude meeting times if they havent changed
@blueprint.route("/bellschedules/<string:school_id>", strict_slashes=False, methods=['GET'])
@check_headers
def list_bellschedules(school_id):
    """
    gets a list of bell schedules
    ---
    parameters:
        - in: path
          name: school_id
          schema:
            type: string
            length: 32
          required: true
    responses:
      200:
        description: A list of bell schedules 
        schema:
          $ref: '#/definitions/BellSchedule'
    
    """

    schedules = BellScheduleDB.query.filter_by(school_id=school_id, soft_deleted=False)

    return respond(BellScheduleSchema(exclude=('school_id',)).dump(schedules, many=True))

@blueprint.route("/bellschedule/<string:bell_schedule_id>", strict_slashes=False, methods=['GET'])
@check_headers
def get_bellschedule(bell_schedule_id):
    """
    gets a single bell schedule
    ---
    parameters:
        - in: path
          name: bell_schedule_id
          schema:
            type: string
            length: 32
          required: true
        - in: header
          name: If-Modified-Since
          schema:
            type: string
            format: date
          required: false
    responses:
      200:
        description: A single of bell schedule 
        schema:
          $ref: '#/definitions/BellSchedule'
    """

    schedule = BellScheduleDB.query.filter_by(
        id=bell_schedule_id, soft_deleted=False).first()

    #double check this
    if schedule is None:
        raise Oops("No bell schedule was found with the specified id.",
                    404, title="Resource Not Found")

    if 'If-Modified-Since' in request.headers:
        since = datetime.strptime(request.headers.get('If-Modified-Since'), HTTP_DATE_FORMAT)
        # TODO: make this a more robust check
        if schedule.last_modified == since:
            return respond(code=304) #Not Modified

    return respond(BellScheduleSchema(exclude=('soft_deleted',)).dump(schedule))


@blueprint.route("/bellschedule", strict_slashes=False, methods=['POST'])
@check_headers
@requires_auth(permissions=[APIScopes.CREATE_BELL_SCHEDULE])
@requires_admin
def create_bellschedule():
    """
    Create a new bell schedule
    ---
    security:
      - ApiKeyAuth: []
    parameters:
        - in: body
          name: schedule
          schema:
            $ref: '#/definitions/BellSchedule'
          required: true
    """

    # get school_id from a data parameter
    school = SchoolDB.query.filter_by(id=school_id).first()
    check_ownership(school)

    new_schedule = BellScheduleSchema().load(get_request_body(request)).data

    school.schedules.append(new_schedule)

    db.session.commit()

    return respond(BellScheduleSchema(exclude=('school_id','soft_deleted')).dump(new_schedule))


@blueprint.route("/bellschedule/<string:bell_schedule_id>", strict_slashes=False, methods=['PATCH'])
@check_headers
@requires_auth(permissions=[APIScopes.EDIT_BELL_SCHEDULE])
@requires_admin
def update_bellschedule(bell_schedule_id):
    """
    Updates a bell schedule
    ---
    security:
      - ApiKeyAuth: []
    parameters:
        - in: path
          name: bell_schedule_id
          schema:
            type: string
            length: 32
          required: true
        - in: body
          name: schedule
          schema:
            $ref: '#/definitions/BellSchedule'
          required: true
        - in: header
          name: If-Unmodified-Since
          schema:
            type: string
            format: date
          required: false
    """

    schedule = BellScheduleDB.query.filter_by(id=bell_schedule_id).first()
    school = SchoolDB.query.filter_by(id=schedule.school_id).first()
    if school is not None:
        check_ownership(school)

    if 'If-Unmodified-Since' in request.headers:
        since = datetime.datetime.strptime(request.headers.get('If-Unmodified-Since'), HTTP_DATE_FORMAT)
        trap_object_modified_since(school.last_modified, since)

    data = get_request_body(request)
    # remove ID from request body if provided because for some reason, the exclude parameter isnt working or may not be correctly getting passed down to the nested/plucked fields
    if data['id']:
        del data['id']

    try:
        updated_schedule = BellScheduleSchema(exclude=('id', 'creation_date')).load(
            data, session=db.session, instance=schedule)
    except ValidationError as err:
        # print(err.messages)  # => {"email": ['"foo" is not a valid email address.']}
        # print(err.valid_data)
        return respond(err.messages, code=400)
        
    db.session.commit()

    return respond(BellScheduleSchema(exclude=('school_id','soft_deleted')).dump(schedule))


@blueprint.route("/bellschedule/<string:bell_schedule_id>", methods=['DELETE'])
@check_headers
@requires_auth(permissions=[APIScopes.DELETE_BELL_SCHEDULE])
@requires_admin
def delete_bellschedule(bell_schedule_id):
    """
    deletes a bell schedule
    ---
    security:
      - ApiKeyAuth: []
    parameters:
        - in: path
          name: bell_schedule_id
          schema:
            type: string
            length: 32
          required: true
        - in: header
          name: If-Unmodified-Since
          schema:
            type: string
            format: date
          required: false
    """

    schedule = BellScheduleDB.query.filter_by(id=bell_schedule_id, soft_deleted=False).first()
    school = SchoolDB.query.filter_by(id=schedule.school_id).first()
    if school is not None:
        check_ownership(school)
    
    if 'If-Unmodified-Since' in request.headers:
        since = datetime.datetime.strptime(request.headers.get('If-Unmodified-Since'), HTTP_DATE_FORMAT)
        trap_object_modified_since(school.last_modified, since)

    schedule.soft_deleted = True
    # db.session.delete(schedule)
    db.session.commit()

    return respond("success", code=204)

#
# Routes
#


# register_api(api, School, "v0", name_of_optional_param="school_id")

# register_api(api, BellSchedule, "v0", url_prefix="/school/<string:school_id>",
#              name_of_optional_param="bell_schedule_id")



@blueprint.before_request
def before():
    current_app.logger.info( "Received request " + request.method + " " + request.path + " for API client '" + get_api_client_id() + "' user '" + get_api_user_id() + "'" )    


@blueprint.after_request
def after_request(response):
    response.headers['Content-Type'] = 'application/json'
    current_app.logger.info( "Handled request with HTTP status: " + str(response.status_code))   
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



# @blueprint.errorhandler(Exception)
# def generic_exception_handler(e):
#     # "We're sorry, but the electrons that were tasked with handling your request became terribly misguided and forgot what it is that they were supposed to be doing. Our team of scientists in the Electron Amnesia Recovery Ward is currently nursing them back to health; if you have any information about what it is these electrons were supposed to be doing at the time of this incident, please contact the maintainer of this service."
#     print("an exception occurred")
#     print(e)
#     return respond(
#         make_error_object(500), code=500, headers={'Content-Type': 'application/json'}
#     )
