
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
	id = db.Column('school_id', HashColumn(length=32),
                        primary_key=True, default=get_uuid)
	owner_id = db.Column('owner_id', db.VARCHAR(length=35))
	full_name = db.Column('school_name', db.VARCHAR(length=75))
	# schedules = db.relationship("BellSchedule")
	acronym = db.Column(
		'school_acronym', db.VARCHAR(length=75), nullable=True)
	alternate_freeperiod_name = db.Column(
		'alternate_freeperiod_name', db.VARCHAR(length=75), nullable=True)
	creation_date = db.Column('creation_date', db.DateTime,
                           default=datetime.utcnow())
	last_modified = db.Column('last_modified', db.DateTime,
                           default=datetime.utcnow(), onupdate=datetime.utcnow)

class BellSchedule(db.Model):
	"""
		description: A BellSchedule
	"""
	__tablename__ = "bellschedules"
	type = "bellschedule"
	id = db.Column('bell_schedule_id', HashColumn(length=32),
                        primary_key=True, default=get_uuid)
	school_id = db.Column(HashColumn(length=32), ForeignKey(School.id))
	name = db.Column('bell_schedule_name', db.VARCHAR(length=75))
	dates = db.relationship("BellScheduleDate")
	#meetingtimes = db.relationship("BellScheduleMeetingTime")
	display_name = db.Column('bell_schedule_display_name', db.VARCHAR(length=75))
	creation_date = db.Column('creation_date', db.DateTime,
                           default=datetime.utcnow())
	last_modified = db.Column('last_modified', db.DateTime,
                           default=datetime.utcnow(), onupdate=datetime.utcnow)

	def get_uri(self, blueprint_name):
        # here the second time blueprint_name is called, it is acting like the api version number
		return url_for(
            blueprint_name + "." + blueprint_name + "_single_bellschedule", school_id=self.id, _external=True)


class BellScheduleDate(db.Model):
	"""
		description: A date during which a particular bell schedule is in effect
	"""
	__tablename__ = "bellscheduledates"
	type = "bellscheduledate"
	type = "date"
	bell_schedule_id = db.Column('bell_schedule_id', HashColumn(length=32), ForeignKey(BellSchedule.id), primary_key=True)
	# school_id = db.Column(HashColumn(length=32), ForeignKey(School.id))
	date = db.Column('date', db.Date, primary_key=True)
	creation_date = db.Column('creation_date', db.DateTime,
                           default=datetime.today().isoformat())


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
	schedule_id = db.Column(HashColumn(length=32), ForeignKey(BellSchedule.id), primary_key=True)
	# school_id = db.Column(HashColumn(length=32), ForeignKey(School.id))
	name = db.Column('classperiod_name', db.VARCHAR(length=75),
                  primary_key=True)
	start_time = db.Column('start_time', db.Time,
                        default=datetime.now().time(),
                        primary_key=True)
	end_time = db.Column('end_time', db.Time,
                      default=datetime.now().time(),
                      primary_key=True)
	creation_date = db.Column('creation_date', db.DateTime,
                           default=datetime.now().isoformat())

	# def get_uri(self, blueprint_name):
	#         # here the second time blueprint_name is called, it is acting like the api version number
	# return url_for(
    #         blueprint_name + "." + blueprint_name + "_single_school", school_id=self.identifier, _external=True)
