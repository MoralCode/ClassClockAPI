from enum import Enum


class AuthType(Enum):
    TOKEN = "Bearer"
    CREDENTIALS = "Basic"


class APIScopes(Enum):
    # Read the name, id, and acronym of every publicly accessible ClassClock school
    READ_SCHOOL_META = "read:school"
    CREATE_SCHOOL = "create:school"
    EDIT_SCHOOL = "edit:school"
    DELETE_SCHOOL = "delete:school"
    READ_BELL_SCHEDULES = "read:bellschedules"
    CREATE_BELL_SCHEDULES = "create:bellschedules"
    EDIT_BELL_SCHEDULES = "edit:bellschedules"
    DELETE_BELL_SCHEDULES = "delete:bellschedules"
