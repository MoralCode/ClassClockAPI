"""
Customized Marshmallow-SQLAlchemy and Marshmallow-JSONAPI Schemas to combine Schema Meta data.
"""
import marshmallow as ma
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema, auto_field
from marshmallow_sqlalchemy.fields import Nested
from marshmallow.fields import Pluck

from common.db_schema import db

from common.db_schema import BellSchedule, BellScheduleMeetingTime, School, BellScheduleDate


# Modified From https://github.com/marshmallow-code/marshmallow-sqlalchemy/commit/cf996b1f448d9b115b083489c8eb96be3bf1dd40#diff-7e28a06588f9d4acda3f3dd4224899afR136
class SessionPluck(Pluck):
    """Pluck field that inherits the session from its parent like Nested does."""

    def _deserialize(self, *args, **kwargs):
        if hasattr(self.schema, "session"):
            try:
                self.schema.session = self.root.session
            except AttributeError:
                # Marshmallow 2.0.0 has no root property.
                self.schema.session = self.parent.session
        return super(Pluck, self)._deserialize(*args, **kwargs)

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
        include_fk = True
    
    creation_date = auto_field(dump_only=True)

class BellScheduleSchema(SQLAlchemyAutoSchema):

    class Meta:
        model = BellSchedule
        include_relationships = True
        load_instance = True
        include_fk = True
    
    id = auto_field(dump_only=True)
    creation_date = auto_field(dump_only=True)
    last_modified = auto_field(dump_only=True)

    meeting_times = Nested(BellScheduleMeetingTimeSchema(), exclude=("schedule_id", "creation_date"), many=True)
    dates = ma.fields.Pluck(BellScheduleDateSchema, "date", many=True)
