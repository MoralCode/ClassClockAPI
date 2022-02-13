from common.db_schema import db
import argparse
from api import create_app
from flask_migrate import stamp
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