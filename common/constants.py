from enum import Enum


class AuthType(Enum):
    TOKEN = "Bearer"
    CREDENTIALS = "Basic"


class APIScopes(Enum):
    # Read the name, id, and acronym of every publicly accessible ClassClock school
    READ_ALL_SCHOOLS = "read:schools-public"
