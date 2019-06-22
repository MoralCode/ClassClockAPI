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
            "endpoint": 'apispec_1',
            "route": '/apispec_1.json',
            "rule_filter": lambda rule: True,  # all in
            "model_filter": lambda tag: True,  # all in
        }
    ],
    "static_url_path": "/flasgger_static",
    # "static_folder": "static",  # must be set by user
    "swagger_ui": True,
    "specs_route": "/docs/"
})


if __name__ == "__main__":
    app.run()
