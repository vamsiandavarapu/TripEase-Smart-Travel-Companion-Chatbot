import sqlite3, bcrypt, os
DB_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'Auth_System', 'auth_users.db')

def db_op(query, params=(), commit=False, fetch=False):
    try:
        with sqlite3.connect(DB_FILE) as conn:
            cur = conn.cursor(); cur.execute(query, params)
            if commit: conn.commit()
            return cur.fetchall() if fetch else True
    except Exception as e: return [] if fetch else (False, str(e))

def init_db():
    db_op('CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, password TEXT NOT NULL, email TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)', commit=True)

def register_user(u, p, e=None):
    hp = bcrypt.hashpw(p.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    res = db_op('INSERT INTO users (username, password, email) VALUES (?, ?, ?)', (u, hp, e), commit=True)
    return (True, "Success") if res is True else (False, "Exists" if "UNIQUE" in str(res) else str(res))

def login_user(u, p):
    res = db_op('SELECT password FROM users WHERE username = ?', (u,), fetch=True)
    if res and bcrypt.checkpw(p.encode('utf-8'), res[0][0].encode('utf-8')): return True, "Success"
    return False, "Invalid credentials"

