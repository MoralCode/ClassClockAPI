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
from auth import db_connection_string
from flask_migrate import Migrate



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
migrate = Migrate(app, db)




if __name__ == "__main__":
    app.run()
else:
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)
