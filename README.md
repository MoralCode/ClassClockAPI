# ClassClockAPI

![Docker Pulls](https://img.shields.io/docker/pulls/moralcode/classclockapi)

This is the backend that provides access to the ClassClock database.

## Environment Variables

| Environment Variable  | Default | Purpose |
| ------------- | ------------- |  ------------- |
| DB_USERNAME  | no default. this value is required  |  The username of the user to connect to the database with  |
| DB_PASSWORD  | no default. this value is required  |  The password of the user to connect to the database with  |
| DB_HOST  | `localhost`  |  the hostname where the database is located  |
| DB_NAME  | `classclock`  |  the name of the database to use if it is different  |
| DB_CONNECTION_URL  |  constructed based on the above values  | Allows the SQLAlchemy connection string to be manually set  |
| AUTH0_DOMAIN   | no default   |  The Auth0 api domain i.e. `yourapp.auth0.com`  |
| API_IDENTIFIER   | no default   |  Your Auth0 api identifier. This may be your API domain name. i.e. `https://api.yourdomain.com` |
| AUTH0_CLIENT_ID   | no default   |  Your Auth0 Client ID  |
| AUTH0_CLIENT_SECRET   | no default   |  Your Auth0 Client Secret   |



## First time Setup

1. Prepare an empty database and have its configuration information handy (login, hostname/port, db name .etc)
2. Install all dependencies (including dev dependencies) using `pipenv install -d`
3. set up a `.env` file with your database configuration settings from earlier 
4. create the db by running `pipenv run python3 createdb.py`. add the `--demo` flag to createdb if you want to include demo data.

After this you should be ready to run the API.

## Docker

This API has been set up to run in a docker container.

The simplest way to run it is to:
1. aquire the container either from a docker repository or by running `docker build . -t classclock-api` in a cloned version of this repo
2. set up the environment variables you want per the above table
3. use a command like `docker run -p 8000:8000 --rm -it --env-file dev.env classclock-api:latest` to run the container interactively using `dev.env` as the source of the environment variables. The app will start up on port 8000.

## Contributing

If you are interested in making changes to the ClassClock API, see the [CONTRIBUTING](./CONTRIBUTING.md) file for details on how to do so. 