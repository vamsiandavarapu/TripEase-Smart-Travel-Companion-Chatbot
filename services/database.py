import sqlite3
import json
import os
from datetime import datetime

DB_FILE = "tripease_user_data.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()

    # User Settings
    c.execute('''CREATE TABLE IF NOT EXISTS user_settings (key TEXT PRIMARY KEY, value TEXT)''')
    # Saved Trips
    c.execute('''CREATE TABLE IF NOT EXISTS saved_trips (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        city TEXT,
        trip_name TEXT,
        start_date TEXT,
        end_date TEXT,
        itinerary_json TEXT,
        created_at TEXT)''')
    
    # Check if username column exists (migration for existing DBs)
    c.execute("PRAGMA table_info(saved_trips)")
    columns = [column[1] for column in c.fetchall()]
    if 'username' not in columns:
        c.execute("ALTER TABLE saved_trips ADD COLUMN username TEXT")
    conn.commit()
    conn.close()

def save_setting(key, value):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO user_settings (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()
    conn.close()

def get_setting(key, default=None):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT value FROM user_settings WHERE key=?", (key,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else default

def save_trip(city, trip_name, start_date, end_date, itinerary_data, username=None):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    itinerary_json = json.dumps(itinerary_data)
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute('''
    INSERT INTO saved_trips (username, city, trip_name, start_date, end_date, itinerary_json, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (username, city, trip_name, str(start_date), str(end_date), itinerary_json, created_at))
    conn.commit()
    conn.close()
    return True

def get_saved_trips(username=None):
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    if username:
        c.execute("SELECT * FROM saved_trips WHERE username=? ORDER BY created_at DESC", (username,))
    else:
        c.execute("SELECT * FROM saved_trips ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()
    return [dict(row) for row in rows]
