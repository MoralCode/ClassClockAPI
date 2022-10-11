from flask import Blueprint, render_template, abort
from jinja2 import TemplateNotFound
from flasgger import APISpec, Schema, Swagger, fields
from apispec.ext.marshmallow import MarshmallowPlugin
from apispec_webframeworks.flask import FlaskPlugin
from common.schemas import *
from blueprints.v0 import *



# docs = Blueprint('docs_pages', __name__, )

def create_docs(app):
        
    # Create an APISpec
    # info: {
    spec = APISpec(
        title="ClassClock API",
        version="0.3.1",
        openapi_version='2.0',
        
        plugins=[
            FlaskPlugin(),
            MarshmallowPlugin(),
        ],
        # options= {
        #     "description": "The development version of the ClassClock API",
        #     "servers": [
        #         {
        #             "url": "https://api.classclock.app/v0",
        #             "description": "ClassClock API Server"
        #         },
        #         {
        #             "url": "https://localhost:8000/v0",
        #             "description": "Dev server"
        #         }
        #     ],
        #     "externalDocs": {
        #         "description": "This API might loosely follow the JSON:API specofocation",
        #         "url": "https://jsonapi.org"
        #     }#,
    #  "contact": {
    #             # "responsibleOrganization": "ME",
    #             # "responsibleDeveloper": "Me",
    #             # "email": "me@me.com",
    #             # "url": "www.me.com",
    #         },
    #         "termsOfService": "http://me.com/terms",
        # }
    )


    template = spec.to_flasgger(
        app,
        definitions=[SchoolSchema, BellScheduleSchema],
        paths=[get_school, get_bellschedule ]
    )


    # config={
    #     "headers": [
    #     ],
        # "specs": [
        #     {
        #         "endpoint": 'apispec_v1',
        #         "route": '/apispec_v1.json',
        #         "rule_filter": lambda rule: True,  # all in
        #         "model_filter": lambda tag: True,  # all in
        #     }
        # ],
    #     "static_url_path": "/flasgger_static",
    #     # "static_folder": "static",  # must be set by user
    #     "swagger_ui": True,
    #     # "specs_route": "/v0/docs/",
    #     "basePath": "/docs",
    #     "host": "api.classclock.app",  # overrides localhost:500
    #     "schemes": [
    #         "https"
    #     ],
    #     "securityDefinitions": {
    #         "ApiKeyAuth": {
    #             "type": "apiKey",
    #             "in": "header",
    #             "name": "Authentication"
    #         }
    #     }
    # },

    # template["basePath"] = "/docs"
    swagger = Swagger(app, template=template)
    return swagger
