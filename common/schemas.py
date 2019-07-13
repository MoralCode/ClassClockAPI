from marshmallow import Schema, fields, post_load
from common.models import SchoolModel


class SchoolSchema(Schema):
    identifier = fields.UUID(load_from='id', dump_to='id')
    full_name = fields.Str(allow_none=True)
    acronym = fields.Str(allow_none=True)
    alternate_freeperiod_name = fields.Str(allow_none=True)
    creation_date = fields.DateTime()
    last_modified = fields.DateTime()

    @post_load
    def make_school(self, data):
        return SchoolModel(**data)
