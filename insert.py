import sqlite3
import os
import uuid
from datetime import datetime, timezone

db_path = os.path.expanduser("~/.mcp-memory/memory.db")
conn = sqlite3.connect(db_path)
print("Connected to db.")

task_id = "8e8e5f18-2b12-47dd-8ee9-2f21fc8b8b05"
project_id = "mcp-memory"
now = datetime.now(timezone.utc).isoformat()

note1_id = uuid.uuid4().hex
note1_title = "UI Initialisation Crash - Missing DOM Element"
note1_text = """During verification of the Global Workspace view with the browser subagent, the UI completely failed to initialize. The app is stuck on "Loading projects..." and an "Internal Server Error" alert pops up. Console logs indicate `els.addGlobalNoteBtn.addEventListener` failed because the element is null. I am now investigating the ID mismatch between `dom.js` and `index.html`."""

note2_id = uuid.uuid4().hex
note2_title = "Missing DOM Element Fix"
note2_text = """The missing `add-global-note-btn` element crash has been fixed. The issue was traced to malformed HTML: when injecting `#global-view`, an extra `</div>` was accidentally introduced right before it, prematurely closing the main wrapper. This corrupted the browser's DOM tree parsing, placing `#add-global-note-btn` outside expected scopes or failing completely. I've corrected the `index.html` structure to properly nest the main layout and panels, ensuring `dom.js` initializes successfully. Re-running the UI verification."""

try:
    with conn:
        conn.execute("INSERT INTO task_notes (id, project_id, task_id, title, note_text, note_type, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                     (note1_id, project_id, task_id, note1_title, note1_text, "investigation", now, now))
        conn.execute("INSERT INTO task_notes (id, project_id, task_id, title, note_text, note_type, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                     (note2_id, project_id, task_id, note2_title, note2_text, "investigation", now, now))
    print("Task notes inserted successfully.")
except Exception as e:
    print(f"Error: {e}")
