
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

from common.guid import HashColumn
import uuid
from datetime import datetime
from flask.helpers import url_for

db = SQLAlchemy()


class School(db.Model):
	"""
		description: A School
	"""
	__tablename__ = "schools"
	type="school"
	identifier = db.Column('school_id', HashColumn(length=16),
	                      primary_key=True, default=uuid.uuid4().hex)
	owner_id = db.Column('owner_id', db.VARCHAR(length=35))
	full_name = db.Column('school_name', db.VARCHAR(length=75))
	acronym = db.Column(
		'school_acronym', db.VARCHAR(length=75), nullable=True)
	alternate_freeperiod_name = db.Column(
		'alternate_freeperiod_name', db.VARCHAR(length=75), nullable=True)
	creation_date = db.Column('creation_date', db.DateTime,
                           default=datetime.utcnow())
	last_modified = db.Column('last_modified', db.DateTime,
                           default=datetime.utcnow(), onupdate=datetime.utcnow)

	def get_uri(self, blueprint_name):
        # here the second time blueprint_name is called, it is acting like the api version number
		return url_for(
            blueprint_name + "." + blueprint_name + "_single_school", school_id=self.identifier, _external=True)
