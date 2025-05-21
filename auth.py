

import os, sys, getpass
from os import environ as env

#default values are only needed for some of these
db_username = env.get("DB_USERNAME")
db_password = env.get("DB_PASSWORD")
db_host = os.getenv("DB_HOST", "localhost")
db_name = os.getenv("DB_NAME", "classclock")

connection_url = f'mysql+mysqlconnector://{db_username}:{db_password}@{db_host}/{db_name}?charset=utf8mb4&collation=utf8mb4_general_ci'
db_connection_string = os.getenv("DB_CONNECTION_URL", connection_url)

db_connection_string = os.getenv("DATABASE_URL", connection_url)

# elif sys.argv[1] == "demo":
# # https://stackoverflow.com/a/46541219
#     with app.app_context():
#         from common.db_schema import *
#         import datetime
#         import time


#         def today_plus(sch, num_days):
#             return BellScheduleDate(school_id = sch, date=datetime.date.today() + datetime.timedelta(days=num_days))

#         s = School(owner_id="1234567890", full_name="Demonstration High School", acronym="DHS")


#         sc1 = BellSchedule(
#             school_id = s.id,
#             name="Even Day",
#             display_name= "Even",
#             dates=[
#                 today_plus(s.id, 0),
#                 today_plus(s.id, 2),
#                 today_plus(s.id, 4)
#                 ]
#         )
    
#         sc2 = BellSchedule(
#             school_id = s.id,
#             name="Odd Day",
#             display_name="Odd",
#             dates=[
#                 today_plus(s.id, 1),
#                 today_plus(s.id, 3)
#                 ]
#         )


#         s.schedules = [sc1,sc2]

        
#         sc1.meeting_times = [
#             BellScheduleMeetingTime(
#                 bell_schedule_id =sc1.id,
#                 name="First Period",
#                 start_time=datetime.time(hour=8, minute=25, second=0, microsecond=0),
#                 end_time=datetime.time(9,25)
#             )
#         ]

#         sc2.meeting_times = [
#             BellScheduleMeetingTime(
#                 bell_schedule_id =sc2.id,
#                 name="First Period",
#                 start_time=datetime.time(8,45),
#                 end_time=datetime.time(9,45)
#             )
            
#         ]

#         db.session.add(s)
#         db.session.commit()
#         print("Done.")
#         exit(0)
    