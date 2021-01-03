import pandas as pd
import requests
import dotenv
import os
import io
import base64
import json
import gspread
from google.oauth2.service_account import (
    Credentials as ServiceAccountCredentials,
)
from datetime import datetime


CAMPUSWIRE_LOGIN_ENTRYPOINT = 'https://api.campuswire.com/v1/auth/login'
CAMPUSWIRE_REPUTATION_URL = "https://api.campuswire.com/v1/group/{}/reputation_report"


class BearerAuth(requests.auth.AuthBase):
    def __init__(self, token):
        self.token = token

    def __call__(self, r):
        r.headers["authorization"] = "Bearer " + self.token
        return r


dotenv.load_dotenv()


def service_account_from_dict(info, scopes=gspread.auth.DEFAULT_SCOPES):
    creds = ServiceAccountCredentials.from_service_account_info(
        info=info, scopes=scopes,
    )
    return gspread.Client(auth=creds)


def get_cw_token(sh):
    # token is stored in the "token" sheet
    # as the token will expire every two weeks, the token is renewed when the script is executed
    try:
        token = sh.worksheet("token").cell(1, 1).value
    except Exception:
        raise Exception("cannot get campuswire token from google sheets")

    response = requests.put(CAMPUSWIRE_LOGIN_ENTRYPOINT, auth=BearerAuth(token))
    if response.ok:
        json_response = response.json()
        token = json_response['token']
        sh.worksheet("token").update("A1", token)
    else:
        raise Exception("cannot get a new campuswire token")

    return token


def get_cw_report(course, group, token):
    response = requests.get(CAMPUSWIRE_REPUTATION_URL.format(group), auth=BearerAuth(token))
    csvio = io.StringIO(response.text)
    return pd.read_csv(csvio)


info = json.loads(base64.b64decode(os.getenv("SERVICEACCOUNT")))
gc = service_account_from_dict(info)
sh = gc.open_by_key(os.getenv("SHEETID"))

token = get_cw_token(sh)


try:
    courses = pd.DataFrame(sh.worksheet("course").get_all_records())
except Exception:
    raise Exception("cannot get campuswire token from google sheets")

wsheets = [ws.title for ws in sh.worksheets()]

for _, c in courses.iterrows():
    if not c["active"]:
        continue

    course = c["course"]
    group = c["group"]

    if course not in wsheets:
        ws = sh.add_worksheet(title=course, rows=0, cols=6)
        ws.update(
            "A1:F1",
            [["last_name", "first_name", "email", "rep_level", "rep_points", "time"]])
    else:
        ws = sh.worksheet(course)

    nrow = len(ws.get_all_values())

    df = get_cw_report(course, group, token)
    df.insert(len(df.columns), "time", datetime.utcnow().isoformat(timespec="seconds"))
    df = df.loc[:, ["last_name", "first_name", "email", "rep_level", "rep_points", "time"]]

    ws.insert_rows(df.values.tolist(), row=nrow+1)
    print("inserted {} rows into {}".format(len(df), course))
