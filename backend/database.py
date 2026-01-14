import sqlite3
from datetime import datetime

DB_NAME = "road_monitoring.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Updated table schema to include location details
    c.execute('''CREATE TABLE IF NOT EXISTS road_logs
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  timestamp TEXT,
                  source_type TEXT,
                  filename TEXT,
                  damage_detected BOOLEAN,
                  severity_score REAL,
                  priority_level TEXT,
                  processed_image_path TEXT,
                  latitude REAL,
                  longitude REAL,
                  address TEXT,
                  municipal_authority TEXT)''')
    conn.commit()
    conn.close()

# Updated function to accept 10 arguments
def insert_log(source_type, filename, damage_detected, severity, priority, processed_path, lat, lng, address, authority):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    c.execute("""INSERT INTO road_logs 
                 (timestamp, source_type, filename, damage_detected, severity_score, priority_level, processed_image_path, latitude, longitude, address, municipal_authority) 
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
              (timestamp, source_type, filename, damage_detected, severity, priority, processed_path, lat, lng, address, authority))
    conn.commit()
    conn.close()

# Initialize on import
init_db()