import gspread
import os
from datetime import datetime
from oauth2client.service_account import ServiceAccountCredentials
import base64
import json
# Setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
json_base64 = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON_BASE64")
decoded = base64.b64decode(json_base64).decode("utf-8")
creds_dict = json.loads(decoded)

creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open_by_key(os.getenv("GOOGLE_SHEET_ID")).sheet1

# Functions
def add_task(user_id, name, due_date):
    sheet.append_row([str(user_id), name, due_date, "pending"])

def mark_task_complete(user_id, name):
    records = sheet.get_all_records()
    for i, row in enumerate(records):
        if row["user_id"] == str(user_id) and row["name"] == name and row["status"] != "complete":
            sheet.update_cell(i + 2, 4, "complete")  # row index + header offset

def get_tasks_due_today():
    today = datetime.today().strftime('%Y-%m-%d')
    records = sheet.get_all_records()
    return [
        {"user_id": row["user_id"], "name": row["name"]}
        for row in records
        if row["due_date"] == today and row["status"] != "complete"
    ]
