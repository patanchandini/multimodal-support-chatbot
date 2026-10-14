import sqlite3

conn = sqlite3.connect("chatbot.db")
rows = conn.execute(
    "SELECT event, details FROM audit_log "
    "WHERE session_id = ? ORDER BY id DESC LIMIT 5",
    ("test-pii",)
).fetchall()

for event, details in rows:
    print(f"{event} -> {details}")