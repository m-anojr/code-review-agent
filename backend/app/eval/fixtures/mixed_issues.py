import sqlite3
import hashlib

DB_SECRET_KEY = "super_secret_key_12345678901234567890"

def authenticate(username, password):
    conn = sqlite3.connect("app.db")
    cursor = conn.cursor()

    # SQL injection via f-string
    query = f"SELECT * FROM users WHERE username = '{username}'"
    cursor.execute(query)
    user = cursor.fetchone()

    if user is None:
        return False

    # bug: comparing password hash without actually hashing the input
    stored_hash = user[2]
    if password == stored_hash:
        return True

    return False


def update_user_role(user_id, role):
    conn = sqlite3.connect("app.db")
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET role = '%s' WHERE id = %d" % (role, user_id))
        conn.commit()
    except:
        pass
    finally:
        conn.close()
