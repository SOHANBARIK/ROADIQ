import sqlite3
import cv2
import numpy as np
import os
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from logic import process_frame
from database import DB_NAME, insert_log
from geo_utils import get_location_details, get_municipal_authority
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Smart Road Monitoring System API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"status": "API is running"}

@app.get("/get-map-data")
def get_map_data():
    try:
        conn = sqlite3.connect(DB_NAME)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # --- UPDATED QUERY: Added 'address' ---
        cursor.execute("SELECT id, timestamp, priority_level, damage_detected, latitude, longitude, municipal_authority, address FROM road_logs ORDER BY id DESC")
        rows = cursor.fetchall()
        conn.close()
        
        results = []
        for row in rows:
            results.append({
                "id": row["id"],
                "timestamp": row["timestamp"],
                "priority": row["priority_level"],
                "lat": row["latitude"],
                "lon": row["longitude"],
                "damage": 1 if row["damage_detected"] else 0,
                "authority": row["municipal_authority"],
                "address": row["address"] # <--- NEW FIELD
            })
        return results
    except Exception as e:
        print(f"Database error: {e}")
        return []

@app.post("/report-incident")
async def report_incident(
    file: UploadFile = File(...),
    latitude: float = Form(...),
    longitude: float = Form(...)
):
    # 1. SPAM CHECK
    if latitude == 0.0 or longitude == 0.0:
        raise HTTPException(status_code=400, detail="Invalid GPS Coordinates")

    # 2. Location Validation
    try:
        in_india, address, city = get_location_details(latitude, longitude)
    except Exception:
        in_india, address, city = True, "Unknown Location", "Unknown City"

    # 3. Process Image
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if frame is None:
        raise HTTPException(status_code=400, detail="Invalid Image")

    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    # CALL LOGIC
    has_damage, severity, priority, save_path = process_frame(rgb_frame, file.filename, "API Upload")
    
    # 4. Determine Authority
    authority_name = get_municipal_authority(city) if has_damage else "N/A"
    
    # 5. Save to Database
    insert_log("API Upload", file.filename, has_damage, severity, priority, save_path, 
               latitude, longitude, address, authority_name)
    
    return {
        "status": "Reported",
        "location": address,
        "priority": priority,
        "severity": severity,
        "authority_notified": authority_name,
        "report_id": "LOGGED"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=10000)