import sqlite3
from config import MEMORY_DB


def init_db():
    conn = sqlite3.connect(MEMORY_DB)
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS memories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT,
        key TEXT,
        value TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    conn.close()


def remember(user_id, key, value):
    conn = sqlite3.connect(MEMORY_DB)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO memories(user_id, key, value) VALUES (?, ?, ?)",
        (str(user_id), key, value)
    )
    conn.commit()
    conn.close()


def recall(user_id):
    conn = sqlite3.connect(MEMORY_DB)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, key, value FROM memories WHERE user_id=? ORDER BY id DESC LIMIT 20",
        (str(user_id),)
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def forget_all(user_id):
    conn = sqlite3.connect(MEMORY_DB)
    cur = conn.cursor()
    cur.execute("DELETE FROM memories WHERE user_id=?", (str(user_id),))
    conn.commit()
    conn.close()


def forget_by_id(memory_id):
    conn = sqlite3.connect(MEMORY_DB)
    cur = conn.cursor()
    cur.execute("DELETE FROM memories WHERE id=?", (memory_id,))
    conn.commit()
    conn.close()


def format_memories(user_id):
    rows = recall(user_id)
    if not rows:
        return "記憶なし"
    return "\n".join([f"{mid}. {key}: {value}" for mid, key, value in rows])


init_db()