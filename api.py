from flask import Flask
from versions import v1
from flask_limiter import Limiter
from flasgger import Swagger
from helpers import get_API_user_identifier

app = Flask(__name__)
limiter = Limiter(app, default_limits=[
                  "25/hour", "5/minute"], key_func=get_API_user_identifier)

app.register_blueprint(v1.blueprint, url_prefix='/v1')


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
        "version": "1.0",
        "description": "The first release of the ClassClock API",
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
            "url": "https://api.classclock.app/v1",
            "description": "ClassClock API Server"
        },
        {
            "url": "https://localhost:5000/v1",
            "description": "Dev server"
        }
    ],
    # "host": "api.classclock.app",  # overrides localhost:500
    # "basePath": "/v1",  # base bash for blueprint registration
    "schemes": [
        "https"
    ]
})


if __name__ == "__main__":
    app.run()
