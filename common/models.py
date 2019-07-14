import datetime
from flask import url_for


class SchoolModel(object):

    def __init__(self, identifier, full_name=None, acronym=None, alternate_freeperiod_name=None, creation_date=None, last_modified=None):
        self.type = "school"
        self.identifier = identifier
        self.full_name = full_name
        self.acronym = acronym
        self.alternate_freeperiod_name = alternate_freeperiod_name
        self.creation_date = creation_date if creation_date is not None else datetime.datetime.now()
        self.last_modified = last_modified if last_modified is not None else datetime.datetime.now()

    def get_uri(self, blueprint_name):
        # here the second time blueprint_name is called, it is acting like the api version number
        return url_for(
            blueprint_name + "." + blueprint_name + "_single_school", school_id=self.identifier.hex, _external=True)

    def __repr__(self):
        return '<School(name={self.full_name!r}, id={self.identifier!r})>'.format(self=self)


class BellScheduleModel(object):

    def __init__(self, identifier, school_id, full_name=None, display_name=None, creation_date=None, last_modified=None):
        self.type = "bellschedule"
        self.identifier = identifier
        self.full_name = full_name
        self.display_name = display_name
        self.school_id = school_id
        self.creation_date = creation_date if creation_date is not None else datetime.datetime.now()
        self.last_modified = last_modified if last_modified is not None else datetime.datetime.now()

    def get_uri(self, blueprint_name):
        # here the second time blueprint_name is called, it is acting like the api version number
        return url_for(
            blueprint_name + "." + blueprint_name + "_single_bellschedule", school_id=self.school_id.hex, bell_schedule_id=self.identifier.hex, _external=True)

    def __repr__(self):
        return '<BellSchedule(name={self.full_name!r}, id={self.identifier.hex!r})>'.format(self=self)
