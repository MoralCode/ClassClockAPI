
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

from common.guid import HashColumn
import uuid
from datetime import datetime, date
from flask.helpers import url_for
from sqlalchemy.sql.schema import ForeignKey

db = SQLAlchemy()

def get_uuid():
	return uuid.uuid4().hex

class School(db.Model):
	"""
		description: A School
	"""
	__tablename__ = "schools"
	type="school"
	identifier = db.Column('school_id', HashColumn(length=16),
                        primary_key=True, default=get_uuid)
	owner_id = db.Column('owner_id', db.VARCHAR(length=35))
	full_name = db.Column('school_name', db.VARCHAR(length=75))
	schedules = db.relationship("BellSchedule")
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


class BellSchedule(db.Model):
	"""
		description: A BellSchedule
	"""
	__tablename__ = "bellschedules"
	type = "bellschedule"
	identifier = db.Column('bell_schedule_id', HashColumn(length=16),
                        primary_key=True, default=get_uuid)
	school_id = db.Column(HashColumn(length=16), ForeignKey('school.identifier'))
	name = db.Column('bell_schedule_name', db.VARCHAR(length=75))
	dates = db.relationship("BellScheduleDate")
	meetingtimes = db.relationship("BellScheduleMeetingTime")
	creation_date = db.Column('creation_date', db.DateTime,
                           default=datetime.utcnow())
	last_modified = db.Column('last_modified', db.DateTime,
                           default=datetime.utcnow(), onupdate=datetime.utcnow)

	def get_uri(self, blueprint_name):
        # here the second time blueprint_name is called, it is acting like the api version number
		return url_for(
            blueprint_name + "." + blueprint_name + "_single_bellschedule", school_id=self.identifier, _external=True)


class BellScheduleDate(db.Model):
	"""
		description: A date during which a particular bell schedule is in effect
	"""
	__tablename__ = "bellschedules"
	type = "bellscheduledate"
	identifier = db.Column('bell_schedule_id', HashColumn(length=16),
                        primary_key=True, default=get_uuid)
	schedule_id = db.Column(HashColumn(length=16), ForeignKey('bellschedule.identifier'))
	name = db.Column('bell_schedule_name', db.VARCHAR(length=75))
	creation_date = db.Column('creation_date', db.Date,
                           default=date.isoformat())


	# def get_uri(self, blueprint_name):
	#         # here the second time blueprint_name is called, it is acting like the api version number
	# return url_for(
    #         blueprint_name + "." + blueprint_name + "_single_school", school_id=self.identifier, _external=True)


class BellScheduleMeetingTime(db.Model):
	"""
		description: A meeting time for a particular bell schedule (aka a class period)
	"""
	__tablename__ = "bellschedulemeetingtimes"
	type = "bellschedulemeetingtime"
	schedule_id = db.Column(HashColumn(length=16), ForeignKey('bellschedule.identifier'))
	school_id = db.Column(HashColumn(length=16), ForeignKey('school.identifier'))
	name = db.Column('classperiod_name', db.VARCHAR(length=75))
	start_time = db.Column('start_time', db.Time,
                        default=datetime.time())
	end_time = db.Column('end_time', db.Time,
                        default=datetime.time())
	creation_date = db.Column('creation_date', db.Date,
                           default=date.isoformat())

	# def get_uri(self, blueprint_name):
	#         # here the second time blueprint_name is called, it is acting like the api version number
	# return url_for(
    #         blueprint_name + "." + blueprint_name + "_single_school", school_id=self.identifier, _external=True)