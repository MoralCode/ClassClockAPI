########################
# UUID for SQLite hack #
########################

from sqlalchemy.types import TypeDecorator, BINARY, CHAR
from sqlalchemy.dialects.postgresql import UUID
import uuid


class HashColumn(TypeDecorator):
    """Platform-independent GUID type.
    Uses PostgreSQL's UUID type, otherwise uses
    CHAR(32), storing as stringified hex values.
    """
    impl = BINARY

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(UUID())
        else:
            return dialect.type_descriptor(BINARY(16))


    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        # elif dialect.name == 'postgresql':
        #     return str(value)
        else:
            if not isinstance(value, uuid.UUID):
                return uuid.UUID(hex=value).bytes
            else:
                return value.bytes

    def process_result_value(self, value, dialect):
        print(value)
        if value is None:
            return value
        else:
            if not isinstance(value, uuid.UUID):

                value = uuid.UUID(bytes=value)
            return value