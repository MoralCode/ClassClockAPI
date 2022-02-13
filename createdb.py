from common.db_schema import db
import argparse
from api import create_app
from flask_migrate import stamp

parser = argparse.ArgumentParser(description='Set up a fresh ClassClock database.')
parser.add_argument('--demo', action='store_true',
                    help='Add some demo data to the database after creation')

args = parser.parse_args()



print("Beginning database creation...")
with create_app().app_context():
	print("Creating tables...")
	db.create_all()
	print("Committing...")
	db.session.commit()


	# then, load the migration configuration and generate the
	# version table, "stamping" it with the most recent rev:
	print("Stamping db version for future upgrades...")
	stamp()
	print("Done creating DB.")

	if args.demo:
		print("Loading Demo Data...")
		from common.db_schema import *
		import datetime
		import time


		def today_plus(sch, num_days):
			return BellScheduleDate(date=datetime.date.today() + datetime.timedelta(days=num_days))

		s = School(owner_id="1234567890", full_name="Demonstration High School", acronym="DHS")


		sc1 = BellSchedule(
			full_name="Even Day",
			display_name= "Even",
			dates=[
				today_plus(s.id, 0),
				today_plus(s.id, 2),
				today_plus(s.id, 4)
				]
		)

		sc2 = BellSchedule(
			full_name="Odd Day",
			display_name="Odd",
			dates=[
				today_plus(s.id, 1),
				today_plus(s.id, 3)
				]
		)


		s.schedules = [sc1,sc2]

		
		sc1.meeting_times = [
			BellScheduleMeetingTime(
				bell_schedule_id =sc1.id,
				name="First Period",
				start_time=datetime.time(hour=8, minute=25, second=0, microsecond=0),
				end_time=datetime.time(9,25)
			)
		]

		sc2.meeting_times = [
			BellScheduleMeetingTime(
				bell_schedule_id =sc2.id,
				name="First Period",
				start_time=datetime.time(8,45),
				end_time=datetime.time(9,45)
			)
			
		]

		db.session.add(s)
		db.session.commit()
		print("Done loading demo data.")
	print("Done")