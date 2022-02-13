from flask import Blueprint, render_template, abort
from jinja2 import TemplateNotFound
from werkzeug.exceptions import HTTPException


main_pages = Blueprint('main_pages', __name__,
                        template_folder='templates')

@main_pages.route("/", methods=['GET'])
def home():
    return render_template('home.html')


@main_pages.errorhandler(HTTPException)
def handle_HTTP_error(e):
    return respond(
        make_error_object(
            e.code, title=e.name, message=e.description),
        code=e.code
    )