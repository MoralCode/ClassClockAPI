from flask import Flask
import logging
from versions import v0
from flask_limiter import Limiter
from flasgger import Swagger
from common.helpers import get_request_origin_identifier
from common.db_schema import db
from os import environ as env

app = Flask(__name__)
limiter = Limiter(app, default_limits=[
                  "25/hour", "5/minute"], key_func=get_request_origin_identifier, headers_enabled=True)

app.register_blueprint(v0.blueprint, url_prefix='/v0')


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
    "specs_route": "/docs/"
},
    template={

    "info": {
        "title": "ClassClock API",
        "version": "0.1",
        "description": "The first beta development version of the ClassClock API",
        "contact": {
            # "responsibleOrganization": "ME",
            # "responsibleDeveloper": "Me",
            # "email": "me@me.com",
            # "url": "www.me.com",
        },
        "termsOfService": "http://me.com/terms",
    },
    "servers": [
        {
            "url": "https://api.classclock.app/",
            "description": "ClassClock API Server"
        },
        {
            "url": "https://localhost:5000/",
            "description": "Dev server"
        }
    ],
    # "host": "api.classclock.app",  # overrides localhost:500
    # "basePath": "/v0",  # base bash for blueprint registration
    "schemes": [
        "https"
    ]
})

app.config.update(
    SQLALCHEMY_DATABASE_URI='mysql+mysqlconnector://{user}:{pw}@{url}/{db}'.format(user=env.get("DB_USERNAME"), pw=env.get("DB_PASSWORD"), url=env.get("DB_HOST"), db="classclock"), DEBUG=True, SQLALCHEMY_TRACK_MODIFICATIONS=False)
db.init_app(app)

if __name__ == "__main__":
    app.run()
else:
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)
