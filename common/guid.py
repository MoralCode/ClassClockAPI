from __future__ import absolute_import
# import uuid
from sqlalchemy import types, func

class HashColumn(types.VARCHAR):

    def bind_expression(self, bindvalue):
        # convert the bind's type from Hex string to binary
        return func.UNHEX(bindvalue)

    def column_expression(self, col):
        # convert select value from binary to hex String
        return func.HEX(col)
