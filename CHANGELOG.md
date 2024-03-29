## 0.3.3
- add optional sentry monitoring
- add TRUSTED_PROXY_COUNT environment variable to allow the app to run behind a proxy
- increase rate limits
- improve handling of 429 errors

## 0.3.2
- Improvements to the admin role checks
- Fix an issue where the token for the auth0management endpoint for checking user roles would expire and cause requests to return less data than they should 

## 0.3.1
- Improvements to logging
- Improved interactions with Auth0 management API by using higher level HTTP libraries and correcting the URL path for accessing the API
- updated role checking for protected endpoints to be a little more robust and more reliably parse the data from the management API

Known issues:
- Will not start up if environment variables are quoted.

## 0.3.0
- Introduce database migrations using flask-migrate.
- Introduce crude soft-deletion
- Add a new endpoint at `/bellschedules` for logged-in admins to list the schedules for every school that they are the owner of
- disable strict slashes on all endpoints (`.../endpoint/` and `.../endpoint` should now act the same.)
- Updates to CORS settings
- Improvements to generated API documententation
- update dependencies and connection string settings to fix some crashing on startup


### Updating to 0.3.0
The recommended/easiest way to update databases created prior to 0.3.0 is to create a new database. However, this may not be possible in all cases.

Alternatively, databases created prior to 0.3.0 should be upgraded as follows:
1. perform a backup
2. determine what commit the database was created from
3. apply any database schema changes (as indicated by changes to the `db_schema.py` file) to get your database up to the same schema as version 0.2.0
4. run the following command against your database: `flask db stamp 93d6649210e1` to set up the versioning table
5. run the migrations using `flask db upgrade`. This will update your database schema so that it contains the latest changes

## 0.2.0
- improved logging
- dependency updates
- begin using sqlalchemy ORM for managing DB queries
- add a mehcanism for populating the database with demo data
- Switch from JSONAPI to a more regular JSON output format
- Create an automatically-generated documentation page with swagger
- add a basic HTML homepage to the API's main URL for any visitors that come looking
- add beta and staging site URLs to CORS origins
- add a /ping endpoint to allow the frontend to check connectivity
- Dockerize the app
## 0.1.0
Initial tagged version