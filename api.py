from flask import Flask, render_template
import logging
from blueprints import v0, main
from docs import create_docs
from flask_limiter import Limiter
from common.helpers import get_request_origin_identifier, make_error_object, respond
from common.db_schema import db
from common.schemas import *
from auth import db_connection_string
from flask_migrate import Migrate

def create_app(config_filename=None):
    app = Flask(__name__)
    if config_filename:
        app.config.from_pyfile(config_filename)

    limiter = Limiter(app, default_limits=[
                  "25/hour", "5/minute"], key_func=get_request_origin_identifier, headers_enabled=True)

    app.register_blueprint(v0.blueprint, url_prefix='/v0')
    app.register_blueprint(main.main_pages)

    app.config.update(SQLALCHEMY_DATABASE_URI=db_connection_string,DEBUG=True, SQLALCHEMY_TRACK_MODIFICATIONS=False)
    db.init_app(app)
    migrate = Migrate(app, db)

    create_docs(app)

    return app


if __name__ == "__main__":
    app.run()
else:
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)
