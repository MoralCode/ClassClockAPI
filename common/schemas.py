from marshmallow import Schema, fields, post_load
from common.models import BellScheduleModel, ClassPeriod
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema, auto_field
from common.db_schema import School


class SchoolSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = School
        include_relationships = True
        load_instance = True
        
    # @post_load
    # def make_school(self, item, many, partial, **kwargs):
    #     return SchoolModel(**item)


class ClassPeriodSchema(Schema):
    name = fields.Str()
    start_time = fields.Time()
    end_time = fields.Time()
    creation_date = fields.DateTime(allow_none=True)

    @post_load
    def make_class_period(self, item, many, partial, **kwargs):
        return ClassPeriod(**item)


class BellScheduleSchema(Schema):
    identifier = fields.UUID(data_key='id')
    full_name = fields.Str(allow_none=True)
    display_name = fields.Str(allow_none=True)
    school_id = fields.UUID(data_key='school_id')
    dates = fields.List(fields.Date())
    meeting_times = fields.Nested(ClassPeriodSchema, many=True)
    creation_date = fields.DateTime(allow_none=True)
    last_modified = fields.DateTime(allow_none=True)

    @post_load
    def make_bell_schedule(self, item, many, partial, **kwargs):
        return BellScheduleModel(**item)
