FROM python:3.8-slim-buster

WORKDIR /classclock-api

RUN pip install pipenv


COPY Pipfile Pipfile.lock /classclock-api/

RUN pipenv install

COPY . /classclock-api/

ENTRYPOINT pipenv run gunicorn --workers 2 --bind 127.0.0.1 api:app
