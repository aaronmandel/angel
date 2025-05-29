import os
import json
import base64
import gspread
from oauth2client.service_account import ServiceAccountCredentials

scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

json_base64 = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON_BASE64")

if not json_base64:
    raise ValueError("Missing GOOGLE_SERVICE_ACCOUNT_JSON_BASE64 environment variable")

decoded = base64.b64decode(json_base64).decode("utf-8")
creds_dict = json.loads(decoded)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

sheet = client.open_by_key(os.getenv("GOOGLE_SHEET_ID")).sheet1

def add_task(user_id, name, due_date):
    sheet.append_row([str(user_id), name, due_date, "no"])

def mark_task_complete(user_id, name):
    records = sheet.get_all_records()
    for i, row in enumerate(records, start=2):
        if str(row["user_id"]) == str(user_id) and row["name"] == name:
            sheet.update_cell(i, 4, "yes")

def get_tasks_due_today():
    from datetime import datetime
    today = datetime.today().strftime("%Y-%m-%d")
    records = sheet.get_all_records()
    return [r for r in records if r["due_date"] == today and r["complete"].lower() != "yes"]

def get_all_tasks():
    return sheet.get_all_records()
