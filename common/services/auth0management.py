import requests
import json
from os import environ as env
import logging

class Auth0ManagementService:

    base_path = "/api/v2"
    base_url = "https://" + env.get("AUTH0_DOMAIN") + base_path 

    headers = {"Content-Type": "application/json"}

    def __init__(self):
        self.access_token = self.get_token()

    def get_user(self, user_id):

        url = Auth0ManagementService.base_url + "/users/" + user_id
        heads = {**Auth0ManagementService.headers, **
                 {"Authorization": "Bearer " + self.access_token}}
        resp = requests.get(url, headers=heads)

        data = resp.json()
        return data
        # print(access_token)

    def get_roles_for_user(self, user_id):
        url = Auth0ManagementService.base_url + "/users/" + user_id + "/roles"
        heads = {**Auth0ManagementService.headers, **
                 {"Authorization": "Bearer " + self.access_token}}
        resp = requests.get(url, headers=heads)
        data = resp.json()
        return data


    def get_token(self):

        # TODO: use the auth0 python SDK/lib for this https://github.com/auth0/auth0-python#management-sdk
        payload = {
            "client_id": env.get("AUTH0_CLIENT_ID"),
            "client_secret": env.get("AUTH0_CLIENT_SECRET"),
            "audience": self.base_url,
            "grant_type": "client_credentials"
        }
        resp = requests.post("https://" + env.get("AUTH0_DOMAIN") + "/oauth/token", data=json.dumps(payload), headers=Auth0ManagementService.headers)

        data = resp.json()
        if data.get("error"):
            logging.error("failed to get auth0 management API access token")
            logging.error(data)
            return ""
        else:
            return data["access_token"]
