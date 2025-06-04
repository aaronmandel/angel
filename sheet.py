import os
import json
import base64
import pytz
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# Setup scope
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

# Load creds from base64 env var
encoded_creds = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON_BASE64")
if not encoded_creds:
    raise EnvironmentError("Missing GOOGLE_SERVICE_ACCOUNT_JSON_BASE64 environment variable")

decoded_creds = base64.b64decode(encoded_creds).decode("utf-8")
service_account_info = json.loads(decoded_creds)
creds = ServiceAccountCredentials.from_json_keyfile_dict(service_account_info, scope)

client = gspread.authorize(creds)

# Load actual spreadsheet name from env
SPREADSHEET_NAME = os.getenv("GOOGLE_SHEET_FILE_NAME", "organiser of doom")

TIMEZONE_SHEET = "timezones"
TASK_SHEET = "tasks"

def get_timezone_sheet():
    try:
        return client.open(SPREADSHEET_NAME).worksheet(TIMEZONE_SHEET)
    except gspread.exceptions.WorksheetNotFound:
        sheet = client.open(SPREADSHEET_NAME)
        tz_sheet = sheet.add_worksheet(title=TIMEZONE_SHEET, rows="100", cols="2")
        tz_sheet.append_row(["user_id", "timezone"])
        return tz_sheet

def get_task_sheet():
    try:
        return client.open(SPREADSHEET_NAME).worksheet(TASK_SHEET)
    except gspread.exceptions.WorksheetNotFound:
        sheet = client.open(SPREADSHEET_NAME)
        task_sheet = sheet.add_worksheet(title=TASK_SHEET, rows="1000", cols="6")
        task_sheet.append_row(["user_id", "name", "due_date", "complete", "recurrence", "priority"])
        return task_sheet

# ------------------ Time Zone ------------------

def set_user_timezone(user_id: str, timezone: str):
    tz_sheet = get_timezone_sheet()
    data = tz_sheet.get_all_records()
    for i, row in enumerate(data, start=2):
        if str(row["user_id"]) == str(user_id):
            tz_sheet.update_cell(i, 2, timezone)
            return
    tz_sheet.append_row([str(user_id), timezone])

def get_user_timezone(user_id):
    tz_sheet = get_timezone_sheet()
    rows = tz_sheet.get_all_records()
    for row in rows:
        if str(row["user_id"]) == str(user_id):
            tz = row.get("timezone", "").strip()
            if tz in pytz.all_timezones:
                return tz
            else:
                print(f"⚠️ Invalid timezone for user {user_id}: '{tz}'")
                return "UTC"
    return "UTC"

# ------------------ Tasks ------------------

def add_task(user_id: str, name: str, due_date: str, recurrence: str = "", priority: str = ""):
    task_sheet = get_task_sheet()
    task_sheet.append_row([str(user_id), name, due_date, "no", recurrence, priority])

def mark_task_complete(user_id: str, name: str):
    task_sheet = get_task_sheet()
    rows = task_sheet.get_all_records()
    for i, row in enumerate(rows, start=2):
        if row.get("user_id") == str(user_id) and row.get("name") == name:
            task_sheet.update_cell(i, 4, "yes")
            return

def delete_task(user_id: str, name: str) -> bool:
    task_sheet = get_task_sheet()
    rows = task_sheet.get_all_records()
    for i, row in enumerate(rows, start=2):
        if row.get("user_id") == str(user_id) and row.get("name") == name:
            task_sheet.delete_rows(i)
            return True
    return False

def edit_task(user_id: str, original_name: str, new_name: str = None, new_due_date: str = None):
    task_sheet = get_task_sheet()
    rows = task_sheet.get_all_records()
    for i, row in enumerate(rows, start=2):
        if row.get("user_id") == str(user_id) and row.get("name") == original_name:
            if new_name:
                task_sheet.update_cell(i, 2, new_name)
            if new_due_date:
                task_sheet.update_cell(i, 3, new_due_date)
            return True
    return False

def get_tasks_due_today():
    task_sheet = get_task_sheet()
    records = task_sheet.get_all_records()
    today = datetime.today().strftime("%Y-%m-%d")
    return [
        r for r in records
        if r.get("due_date") == today and r.get("complete", "").lower() != "yes"
    ]

def get_all_tasks():
    return get_task_sheet().get_all_records()
