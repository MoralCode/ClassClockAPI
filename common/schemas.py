from marshmallow import Schema, fields, post_load
from common.models import SchoolModel, BellScheduleModel


class SchoolSchema(Schema):
    identifier = fields.UUID(load_from='id', dump_to='id')
    full_name = fields.Str(allow_none=True)
    acronym = fields.Str(allow_none=True)
    alternate_freeperiod_name = fields.Str(allow_none=True)
    creation_date = fields.DateTime(allow_none=True)
    last_modified = fields.DateTime(allow_none=True)

    @post_load
    def make_school(self, data):
        return SchoolModel(**data)


class BellScheduleSchema(Schema):
    identifier = fields.UUID(load_from='id', dump_to='id')
    full_name = fields.Str(allow_none=True)
    display_name = fields.Str(allow_none=True)
    school_id = fields.UUID(load_from='school_id', dump_to='school_id')
    creation_date = fields.DateTime()
    last_modified = fields.DateTime()

    @post_load
    def make_bell_schedule(self, data):
        return BellScheduleModel(**data)
