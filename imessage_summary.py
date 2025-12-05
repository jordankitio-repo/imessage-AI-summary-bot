import sqlite3
import os
from datetime import datetime, timedelta
import subprocess
from google import genai
import unicodedata
import time

# -------------------------------
# Configuration
# -------------------------------
CHAT_NAME = "SLIMEZ surviving misandry "
TRIGGER = "summarize chat"  # message that triggers the summary
CHECK_INTERVAL = 10          # seconds between checks
DB_PATH = os.path.expanduser("~/Library/Messages/chat.db")
HOURS = 12

# -------------------------------
# Gemini API client
# -------------------------------
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    raise ValueError("Please set GEMINI_API_KEY environment variable")

client = genai.Client(api_key=API_KEY)

# -------------------------------
# Helper functions
# -------------------------------
def get_chat_id():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT ROWID FROM chat WHERE display_name LIKE ?", (f"%{CHAT_NAME}%",))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

def get_recent_messages(chat_id, since_timestamp):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
    SELECT text
    FROM message
    JOIN chat_message_join ON message.ROWID = chat_message_join.message_id
    WHERE chat_message_join.chat_id = ?
      AND text IS NOT NULL
      AND date/1000000000 >= ?
    ORDER BY date ASC
    """, (chat_id, since_timestamp))
    rows = c.fetchall()
    conn.close()
    return [text for (text,) in rows]

def summarize_messages(messages):
    # Return early if there are no messages
    if not messages:
        return "No recent messages to summarize."

    prompt = (
        "Summarize what this iMessage group conversation is about. "
        "What are people discussing or planning, each in bullet points of 1-3 short sentences "
        "with the minimal amount of words to provide the most context. Ignore messages that are "
        "just commands or test messages, and start with the topic that has the most reactions "
        "and interactions. this summary should be 10 bullet points max:\n\n"
        + "\n".join(messages)
    )

    # Try the modern Responses API first (common in google genai SDKs)
    try:
        response = client.responses.create(
            model="gemini-2.5-flash",
            input=prompt
        )
    except Exception:
        # Fallback for older/alternate SDK method if present
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[{"text": prompt}]
            )
            # many older responses expose a top-level text field
            text = getattr(response, "text", None)
            if text:
                return text.strip()
            # try common dict shape
            if hasattr(response, "candidates"):
                try:
                    return response.candidates[0].content.strip()
                except Exception:
                    pass
            return str(response)
        except Exception as e:
            # If both methods fail, surface a helpful message
            return f"Error generating summary: {e}"

    # Prefer output_text if available
    text = getattr(response, "output_text", None)
    if text:
        return text.strip()

    # Try common nested shapes: response.output[0].content[0].text
    try:
        return response.output[0].content[0].text.strip()
    except Exception:
        pass

    # Generic extraction: iterate over output -> content entries and collect any text-like fields
    texts = []
    for out in getattr(response, "output", []) or []:
        for content in getattr(out, "content", []) or []:
            if isinstance(content, dict):
                t = content.get("text") or content.get("output_text") or content.get("content")
            else:
                t = getattr(content, "text", None)
            if t:
                texts.append(t)
    if texts:
        return "\n".join(texts).strip()

    # Last-resort stringification
    return "Unable to parse model response for summary."

def sanitize_for_applescript(text):
    safe_summary = unicodedata.normalize("NFKD", text)
    safe_summary = safe_summary.encode("ascii", "ignore").decode()
    safe_summary = safe_summary.replace('\\', '\\\\').replace('"', '\\"').replace('\n', ' ')
    return safe_summary

def send_summary_to_chat(summary):
    escaped_summary = sanitize_for_applescript(summary)
    applescript = f'''
    tell application "Messages"
        set targetChat to first chat whose name contains "{CHAT_NAME}"
        set messageText to "🕒 Summary of last {HOURS} hour(s): {escaped_summary}"
        send messageText to targetChat
    end tell
    '''
    subprocess.run(["osascript", "-"], input=applescript, text=True, check=True)
    print("Summary sent to chat successfully.")

# -------------------------------
# Main loop
# -------------------------------
last_checked = int((datetime.now() - timedelta(hours=HOURS)).timestamp() - 978307200)
chat_id = get_chat_id()
if not chat_id:
    print("Chat not found.")
    exit()

print(f"Monitoring '{CHAT_NAME}' for trigger '{TRIGGER}'...")

while True:
    recent_messages = get_recent_messages(chat_id, last_checked)
    last_checked = int(datetime.now().timestamp() - 978307200)
    
    for msg in recent_messages:
        if msg.strip().lower() == TRIGGER.lower():
            print("Trigger detected! Summarizing chat...")
            all_messages = get_recent_messages(chat_id, last_checked - HOURS*3600)  # last N hours
            summary = summarize_messages(all_messages)
            send_summary_to_chat(summary)
            break  # prevent double-sending

    time.sleep(CHECK_INTERVAL)