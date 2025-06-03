import re
import dateparser
from datetime import datetime

def parse_command(message: str) -> dict:
    message_lower = message.lower()
    
    result = {
        "action": None,
        "name": None,
        "due_date": None,
        "recurrence": "",
        "priority": ""
    }

    # Detect action
    if any(word in message_lower for word in ["complete", "done", "mark"]):
        result["action"] = "complete"
    elif any(word in message_lower for word in ["add", "create", "schedule"]):
        result["action"] = "add"
    else:
        result["action"] = "add"  # fallback

    # Extract recurrence
    if "every day" in message_lower or "daily" in message_lower:
        result["recurrence"] = "daily"
    elif "every week" in message_lower or "weekly" in message_lower:
        result["recurrence"] = "weekly"
    elif "every month" in message_lower or "monthly" in message_lower:
        result["recurrence"] = "monthly"
    elif match := re.search(r"every (\w+day)", message_lower):
        result["recurrence"] = match.group(1)

    # Extract priority (first hashtag match)
    if tag_match := re.search(r"#(\w+)", message):
        result["priority"] = tag_match.group(1).lower()

    # Extract due date
    parsed_date = dateparser.parse(message, settings={'PREFER_DATES_FROM': 'future'})
    if parsed_date:
        result["due_date"] = parsed_date.strftime("%Y-%m-%d")

    # Extract task name
    if result["action"] == "add":
        # Match everything between "add ..." and "by"/"on"/recurrence/hashtag
        name_match = re.search(r"(?:add|create|schedule)\s+(.*?)(?:\s+(by|on|every|#)\s+|$)", message_lower)
        if name_match:
            result["name"] = name_match.group(1).strip()
    elif result["action"] == "complete":
        name_match = re.search(r"(?:complete|done|mark)\s+(.*)", message_lower)
        if name_match:
            result["name"] = name_match.group(1).strip()

    return result
