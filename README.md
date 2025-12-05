# imessage-AI-summary-bot
local automation tool that monitors a user’s iMessage group chat on macOS, listens for a keyword trigger (“summarize chat”), and automatically summarizes the conversation from the past hour using Google’s Gemini API.
Key Features

Automated Conversation Summaries – Generates concise summaries of group messages.

Natural Language Understanding – Uses Gemini’s large language model for summarization.

iMessage Integration – Reads and sends messages directly using the macOS Messages database and AppleScript.

Trigger-based Execution – Responds to a specific user message (“summarize chat”) in real time.

Local Privacy – Runs entirely on-device; only the selected text batch is sent to Gemini’s API.

Configurable – Adjustable time window (HOURS) and polling interval (CHECK_INTERVAL).
