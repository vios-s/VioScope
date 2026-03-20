import json
from datetime import datetime
from pathlib import Path

import viosclaw.config as config


def slugify(text: str) -> str:
    # 1. lowercase
    # 2. replace anything that's not a-z, 0-9 with "_"
    # 3. strip leading/trailing underscores
    text = text.lower()
    text = "".join(c if c.isalnum() else "_" for c in text)
    text = text.strip("_")
    return text


def new_session(first_input: str) -> tuple[str, Path]:
    # The session id would be timestamp YYMMDD and slugified first 30 chars
    id = datetime.now().strftime("%y%m%d") + "-" + slugify(first_input[:30]) + ".jsonl"
    session_path = config.SESSIONS_DIR / id
    session_path.parent.mkdir(parents=True, exist_ok=True)
    return id, session_path


def save_message(session_path: Path, message: dict) -> None:
    # open file in append mode and write the message as json
    with open(session_path, "a") as f:
        json.dump(message, f)
        f.write("\n")  # write a newline after each message


def load_messages(session_path: Path) -> list[dict]:
    # read line by line and return the list
    messages = []

    if not session_path.exists():
        return []
    with open(session_path, "r") as f:
        for line in f:
            messages.append(json.loads(line))
    return messages
