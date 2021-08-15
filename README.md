# ClassClockAPI

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



## Setup command

To run the setup script, first create an empty database and a new user that can access the database. Then, with the environment variables set appropriately as listed above, execute `python3 api.py setup`. If you have not specified the `DB_USERNAME` or `DB_PASSWORD` environment variables, you will be prompted for them interactively when the script runs.

## Docker

This API has been set up to run in a docker container.

The simplest way to run it is to:
1. aquire the container either from a docker repository or by running `docker build . -t classclock-api` in a cloned version of this repo
2. set up the environment variables you want per the above table
3. use a command like `docker run -p 8000:8000 --rm --env-file dev.env classclock-api:latest` to run the container interactively using `dev.env` as the source of the environment variables. The app will start up on port 8000.