"""
Customized Marshmallow-SQLAlchemy and Marshmallow-JSONAPI Schemas to combine Schema Meta data.
"""
import marshmallow as ma
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema

from common.db_schema import db

from common.db_schema import BellSchedule, BellScheduleMeetingTime, School, BellScheduleDate


class SchoolSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = School
        include_relationships = True
        load_instance = True
        include_fk = True

class BellScheduleDateSchema(SQLAlchemyAutoSchema):

    class Meta:
        model = BellScheduleDate
        include_relationships = True
        load_instance = True
        include_fk = True

class BellScheduleMeetingTimeSchema(SQLAlchemyAutoSchema):
    class Meta:
        model = BellScheduleMeetingTime
        include_relationships = True
        load_instance = True
        include_fk = True

class BellScheduleSchema(SQLAlchemyAutoSchema):

    class Meta:
        model = BellSchedule
        include_relationships = True
        load_instance = True
        include_fk = True

        # Pluck dates and meeting times?
