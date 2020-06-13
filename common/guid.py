from __future__ import absolute_import
import uuid
from sqlalchemy import types, func

#https://docs.sqlalchemy.org/en/13/core/custom_types.html#backend-agnostic-guid-type
class HashColumn(types.TypeDecorator):
    impl=types.BINARY

    def process_bind_param(self, value, dialect):
        if value is not None:
            return uuid.UUID(hex=value).bytes

    def process_result_value(self, value, dialect):
        return uuid.UUID(bytes=value).hex
        
    # This is a shallow copy and is provided to fulfill part of the TypeEngine contract. It usually does not need to be overridden unless the user-defined TypeDecorator has local state that should be deep-copied.
    # def copy(self, **kw):
    #     return HashColumn(32)