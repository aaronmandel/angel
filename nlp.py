import os
import openai
import dateparser
from datetime import datetime

openai.api_key = os.getenv("OPENAI_API_KEY")

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
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )

        content = response.choices[0].message.content.strip()
        print("🔍 Raw OpenAI Output:", content)

        parsed = eval(content)  # You can swap to json.loads() if GPT is strict JSON

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
