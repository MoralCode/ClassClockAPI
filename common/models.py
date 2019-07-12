import datetime


class SchoolModel(object):

    def __init__(self, identifier, full_name, acronym, alternate_freeperiod_name=None, creation_date=None):
        self.type = "school"
        self.identifier = identifier
        self.full_name = full_name
        self.acronym = acronym
        self.alternate_freeperiod_name = alternate_freeperiod_name
        self.creation_date = creation_date if creation_date is not None else datetime.datetime.now()

    def __repr__(self):
        return '<User(name={self.full_name!r}, id={self.identifier!r})>'.format(self=self)
