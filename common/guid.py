from __future__ import absolute_import
import uuid
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import types, func

#https://docs.sqlalchemy.org/en/13/core/custom_types.html#backend-agnostic-guid-type
class HashColumn(types.TypeDecorator):
    impl=types.CHAR

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(UUID())
        else:
            return dialect.type_descriptor(types.BINARY(16))


    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        elif dialect.name == 'postgresql':
            return uuid.UUID(value)
        else:
            if not isinstance(value, uuid.UUID):
                return uuid.UUID(value).bytes
            else:
                # bytes
                return value.bytes

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        else:
            return uuid.UUID(bytes=value).hex
        
    # This is a shallow copy and is provided to fulfill part of the TypeEngine contract. It usually does not need to be overridden unless the user-defined TypeDecorator has local state that should be deep-copied.
    # def copy(self, **kw):
    #     return HashColumn(32)