from flask import Flask, render_template
import logging
from blueprints import v0, main
from docs import create_docs
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from common.helpers import make_error_object, respond
from common.db_schema import db
from common.schemas import *
from auth import db_connection_string
from flask_migrate import Migrate
from os import environ as env

if env.get("SENTRY_DSN"):
    import sentry_sdk
    sentry_sdk.init(
        dsn=env.get("SENTRY_DSN"),
        # Set traces_sample_rate to 1.0 to capture 100%
        # of transactions for performance monitoring.
        # We recommend adjusting this value in production.
        traces_sample_rate=1.0
    )

def create_app(config_filename=None):
    app = Flask(__name__)
    if config_filename:
        app.config.from_pyfile(config_filename)

    limiter = Limiter(get_remote_address, app=app, default_limits=[
                  "25/hour", "5/minute"], headers_enabled=True)

    app.register_blueprint(v0.blueprint, url_prefix='/v0')
    app.register_blueprint(main.main_pages)

    app.config.update(SQLALCHEMY_DATABASE_URI=db_connection_string,DEBUG=True, SQLALCHEMY_TRACK_MODIFICATIONS=False)
    db.init_app(app)
    migrate = Migrate(app, db)

    create_docs(app)

    return app


if __name__ == "__main__":
    create_app().run()
else:
    app=create_app()
    gunicorn_logger = logging.getLogger('gunicorn.error')
    app.logger.handlers = gunicorn_logger.handlers
    app.logger.setLevel(gunicorn_logger.level)
