import sqlite3, pickle, os

# Bug 1: SQL injection
def get_user(username):
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE name = '" + username + "'")  
    return cursor.fetchall()
    # resource leak: conn never closed

# Bug 2: hardcoded secret
API_KEY = "sk-prod-abc123secret"

# Bug 3: unsafe deserialization
def load_data(blob):
    return pickle.loads(blob)

# Bug 4: bare except
def risky():
    try:
        os.remove("/tmp/file")
    except:
        pass
