import os
import dateparser
import json
from datetime import datetime
from openai import OpenAI

client = OpenAI()  # Automatically uses OPENAI_API_KEY from env

def parse_command(input_text):
    prompt = f"""
You are a task assistant that extracts task instructions from user input.

Your output **must be in strict JSON format** using these keys:
- "action": "add" or "complete"
- "name": the name of the task (string)
- "due_date": the due date in natural language (e.g., "in 2 days", "by end of month"). If none, use null.

Only respond with JSON. Do not explain or comment.

User input:
\"\"\"{input_text}\"\"\"
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )

        content = response.choices[0].message.content.strip()
        print("🔍 Raw OpenAI Output:", content)

        parsed = json.loads(content)  # Use json.loads, not eval

        # Parse natural language due_date → YYYY-MM-DD
        raw_due = parsed.get("due_date")
        parsed_date = dateparser.parse(
            raw_due,
            settings={
                "PREFER_DATES_FROM": "future",
                "RELATIVE_BASE": datetime.now(),
                "PARSERS": ["relative-time", "absolute-time", "custom-formats"]
            }
        )

        parsed["due_date"] = parsed_date.strftime("%Y-%m-%d") if parsed_date else None
        return parsed

    except Exception as e:
        print("❌ Parse error:", e)
        return {"action": None, "name": None, "due_date": None}
