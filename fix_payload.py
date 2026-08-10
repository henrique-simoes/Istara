import sqlite3
import json

db_path = "/Users/user/Documents/Istara-main-pi-replacement/.compass-forge/state.sqlite3"
conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute("SELECT id, payload_json FROM tasks WHERE public_id = 'FIX-pi-eval-REVIEW-r1'")
row = cur.fetchone()
if row:
    task_id, payload_str = row
    payload = json.loads(payload_str)
    payload["source_task"] = "pi-eval-REVIEW"
    cur.execute("UPDATE tasks SET payload_json = ? WHERE id = ?", (json.dumps(payload), task_id))
    conn.commit()
    print("Updated successfully.")
else:
    print("Task not found.")
conn.close()
