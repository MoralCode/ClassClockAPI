# -*- coding: utf-8 -*-
# this file was copied from https://github.com/miLibris/flask-rest-jsonapi/blob/ad3f90f81955fa41aaf0fb8c49a75a5fbe334f5f/flask_rest_jsonapi/errors.py under the terms of the MIT license.


"""Helper to  format Api errors according to jsonapi specification"""


def jsonapi_errors(jsonapi_errors):
    """Construct api error according to jsonapi 1.0

    :param iterable jsonapi_errors: an iterable of jsonapi error
    :return dict: a dict of errors according to jsonapi 1.0
    """
    return {'errors': [jsonapi_error for jsonapi_error in jsonapi_errors],
            'jsonapi': {'version': '1.0'}}
