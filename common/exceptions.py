# Format error response and append status code.

class AuthError(Exception):
    def __init__(self, error, status_code):
        self.error = error
        self.status_code = status_code


class Oops(Exception):
    def __init__(self, message, status_code, title=None):
        self.message = message
        self.status_code = status_code
        self.title = title