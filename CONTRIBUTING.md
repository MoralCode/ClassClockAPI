# Contributing to the ClassClock API


Here are some things that may be helpful for maintainers or contributors


## making changes to the schema
If you make changes to the DB schema, generate a new migration to allow existing users to upgrade their databases. This can be done with the command `FLASK_APP=api.py pipenv run flask db migrate -m "<message>"`. Use a short, descriptive message to describe what was changed. TO upgrade, run `FLASK_APP=api.py pipenv run flask db upgrade` to update your local db to the new schema. Don't forget to also document the changes in the changelog you made to the app and which app versions are compatible with which DB versions.

