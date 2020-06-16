"""
Customized Marshmallow-SQLAlchemy and Marshmallow-JSONAPI Schemas to combine Schema Meta data.
"""
import marshmallow as ma
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema, auto_field

from common.db_schema import db

from common.db_schema import BellSchedule, BellScheduleMeetingTime, School, BellScheduleDate


class SchoolSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = School
        include_relationships = False
        load_instance = True
        include_fk = False
    
    id = auto_field(dump_only=True)
    creation_date = auto_field(dump_only=True)
    last_modified = auto_field(dump_only=True)

class BellScheduleDateSchema(SQLAlchemyAutoSchema):

    class Meta:
        model = BellScheduleDate
        include_relationships = False
        load_instance = True
        include_fk = False
    
    creation_date = auto_field(dump_only=True)


class BellScheduleMeetingTimeSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = BellScheduleMeetingTime
        include_relationships = False
        load_instance = True
        include_fk = False
    
    creation_date = auto_field(dump_only=True)

class BellScheduleSchema(SQLAlchemyAutoSchema):

    class Meta:
        model = BellSchedule
        include_relationships = False
        load_instance = True
        include_fk = False
    
    id = auto_field(dump_only=True)
    creation_date = auto_field(dump_only=True)
    last_modified = auto_field(dump_only=True)

        # Pluck dates and meeting times?
