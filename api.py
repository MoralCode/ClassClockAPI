from flask import Flask, render_template
import logging
from versions import v0
from flask_limiter import Limiter
from flasgger import Swagger
from common.helpers import get_request_origin_identifier, make_error_object, respond
from common.db_schema import db
from common.schemas import *
from flasgger import APISpec, Schema, Swagger, fields
from apispec.ext.marshmallow import MarshmallowPlugin
from apispec_webframeworks.flask import FlaskPlugin
import os, sys, getpass
from os import environ as env
from werkzeug.exceptions import HTTPException


#default values are only needed for some of these
db_username = env.get("DB_USERNAME")
db_password = env.get("DB_PASSWORD")
db_host = os.getenv("DB_HOST", "localhost")
db_name = os.getenv("DB_NAME", "classclock")

if sys.argv[1] in ("setup", "demo"):
    if not env.get("DB_CONNECTION_URL"):
        if not db_username:
            db_username = input('database username: ')
        if not db_password:
            db_password = getpass.getpass('database password (input not shown): ')


db_connection_string=os.getenv("DB_CONNECTION_URL", 
    'mysql+mysqlconnector://{user}:{pw}@{url}/{db}'.format(
        user=db_username,
        pw=db_password,
        url=db_host,
        db=db_name
    )
)

app = Flask(__name__)
limiter = Limiter(app, default_limits=[
                  "25/hour", "5/minute"], key_func=get_request_origin_identifier, headers_enabled=True)

app.register_blueprint(v0.blueprint, url_prefix='/v0')


# Create an APISpec
#info: {
spec = APISpec(
    title="ClassClock API",
    version="0.1",
    openapi_version='2.0',
    plugins=[
        FlaskPlugin(),
        MarshmallowPlugin(),
    ],
    options= {
        "description": "The development version of the ClassClock API",
        "servers": [
            {
                "url": "https://api.classclock.app/v0",
                "description": "ClassClock API Server"
            },
            {
                "url": "https://localhost:8000/v0",
                "description": "Dev server"
            }
        ],
        "externalDocs": {
            "description": "This API might loosely follow the JSON:API specofocation",
            "url": "https://jsonapi.org"
        }#,
#  "contact": {
#             # "responsibleOrganization": "ME",
#             # "responsibleDeveloper": "Me",
#             # "email": "me@me.com",
#             # "url": "www.me.com",
#         },
#         "termsOfService": "http://me.com/terms",
    }
)


template = spec.to_flasgger(
    app,
    definitions=[SchoolSchema, BellScheduleSchema],
    paths=[]
)

swagger = Swagger(app, config={
    "headers": [
    ],
    "specs": [
        {
            "endpoint": 'apispec_v1',
            "route": '/apispec_v1.json',
            "rule_filter": lambda rule: True,  # all in
            "model_filter": lambda tag: True,  # all in
        }
    ],
    "static_url_path": "/flasgger_static",
    # "static_folder": "static",  # must be set by user
    "swagger_ui": True,
    "specs_route": "/v0/docs/",
    "basePath": "/v0",
    "host": "api.classclock.app",  # overrides localhost:500
    "schemes": [
        "https"
    ],
    "securityDefinitions": {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "Authentication"
        }
    }
},
template=template)



app.config.update(SQLALCHEMY_DATABASE_URI=db_connection_string,DEBUG=True, SQLALCHEMY_TRACK_MODIFICATIONS=False)
db.init_app(app)

if sys.argv[1] == "setup":
# https://stackoverflow.com/a/46541219
    with app.app_context():
        db.create_all()
        db.session.commit()
        print("Done.")
        exit(0)
elif sys.argv[1] == "demo":
# https://stackoverflow.com/a/46541219
    with app.app_context():
        from common.db_schema import *
        import datetime
        import time


        def today_plus(sch, num_days):
            return BellScheduleDate(school_id = sch, date=datetime.date.today() + datetime.timedelta(days=num_days))

        s = School(owner_id="1234567890", full_name="Demonstration High School", acronym="DHS")


        sc1 = BellSchedule(
            school_id = s.id,
            name="Even Day",
            display_name= "Even",
            dates=[
                today_plus(s.id, 0),
                today_plus(s.id, 2),
                today_plus(s.id, 4)
                ]
        )
    
        sc2 = BellSchedule(
            school_id = s.id,
            name="Odd Day",
            display_name="Odd",
            dates=[
                today_plus(s.id, 1),
                today_plus(s.id, 3)
                ]
        )


        s.schedules = [sc1,sc2]

        
        sc1.meeting_times = [
            BellScheduleMeetingTime(
                schedule_id =sc1.id,
                name="First Period",
                start_time=datetime.time(hour=8, minute=25, second=0, microsecond=0),
                end_time=datetime.time(9,25)
            )
        ]

        sc2.meeting_times = [
            BellScheduleMeetingTime(
                schedule_id =sc2.id,
                name="First Period",
                start_time=datetime.time(8,45),
                end_time=datetime.time(9,45)
            )
            
        ]

        db.session.add(s)
        db.session.commit()
        print("Done.")
        exit(0)
    

@app.errorhandler(HTTPException)
def handle_HTTP_error(e):
    return respond(
        make_error_object(
            e.code, title=e.name, message=e.description),
        code=e.code
    )


@app.route("/", methods=['GET'])
def home():
    return render_template('home.html')



if __name__ == "__main__":
    app.run()
else:
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)
