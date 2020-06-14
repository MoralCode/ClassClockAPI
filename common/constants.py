from enum import Enum

HTTP_DATE_FORMAT = '%a, %d %b %Y %H:%M:%S GMT'

class AuthType(Enum):
    TOKEN = "Bearer"
    CREDENTIALS = "Basic"


class APIScopes(Enum):
    # Read the name, id, and acronym of every publicly accessible ClassClock school
    READ_SCHOOL = "read:school"
    CREATE_SCHOOL = "create:school"
    EDIT_SCHOOL = "edit:school"
    DELETE_SCHOOL = "delete:school"
    READ_BELL_SCHEDULE = "read:bellschedule"
    CREATE_BELL_SCHEDULE = "create:bellschedule"
    EDIT_BELL_SCHEDULE = "edit:bellschedule"
    DELETE_BELL_SCHEDULE = "delete:bellschedule"
    LIST_SCHOOLS = "list:school"
    LIST_BELL_SCHEDULES = "list:bellschedule"
