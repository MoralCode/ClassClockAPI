from marshmallow import Schema, fields, post_load
from common.models import BellScheduleModel, ClassPeriod
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema, auto_field
from common.db_schema import BellSchedule, BellScheduleMeetingTime, School


class SchoolSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = School
        include_relationships = True
        load_instance = True
        
class BellScheduleSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = BellSchedule
        include_relationships = True
        load_instance = True
        include_fk = True

    # @post_load
    # def make_bell_schedule(self, item, many, partial, **kwargs):
    #     return BellScheduleModel(**item)


class ClassPeriodSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = BellScheduleMeetingTime
        include_relationships = True
        load_instance = True
        include_fk = True
