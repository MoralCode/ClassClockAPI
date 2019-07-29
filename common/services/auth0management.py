import http.client
import json
from os import environ as env


class Auth0ManagementService:

    base_path = "/api/v2"

    headers = {"Content-Type": "application/json"}

    def __init__(self):
        self.conn = http.client.HTTPSConnection("classclock.auth0.com")
        self.access_token = self.get_token()

    def get_user(self, user_id):

        url = Auth0ManagementService.base_path + "/users/" + user_id
        heads = {**Auth0ManagementService.headers, **
                 {"Authorization": "Bearer " + self.access_token}}
        self.conn.request("GET", url, "", heads)

        res = self.conn.getresponse()
        data = res.read()

        return data.decode("utf-8")
        # print(access_token)

    def update_user_app_metadata(self, user_id, app_metadata):

        url = Auth0ManagementService.base_path + "/users/" + user_id
        heads = {**Auth0ManagementService.headers, **
                 {"Authorization": "Bearer " + self.access_token}}
        self.conn.request("PATCH", url, {"app_metadata": app_metadata}, heads)

        res = self.conn.getresponse()
        data = res.read()

        return data.decode("utf-8")
        # print(access_token)

    def get_roles_for_user(self, user_id):
        url = Auth0ManagementService.base_path + "/users/" + user_id + "/roles"
        heads = {**Auth0ManagementService.headers, **
                 {"Authorization": "Bearer " + self.access_token}}
        self.conn.request("GET", url, "", heads)

        res = self.conn.getresponse()
        data = res.read()

        return data.decode("utf-8")

    def get_token(self):
        payload = "{\"client_id\": \"" + env.get("AUTH0_CLIENT_ID") + "\" ,\"client_secret\": \"" + env.get(
            "AUTH0_CLIENT_SECRET") + "\" ,\"audience\": \"https://classclock.auth0.com/api/v2/\",\"grant_type\": \"client_credentials\"}"

        self.conn.request("POST", "/oauth/token", payload,
                          Auth0ManagementService.headers)

        res = self.conn.getresponse()
        data = res.read()
        return json.loads(data.decode("utf-8"))["access_token"]
