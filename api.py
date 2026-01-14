# import cv2
# import numpy as np
# from fastapi import FastAPI, UploadFile, File, Form, HTTPException
# from logic import process_frame
# from database import insert_log
# # IMPORT THE NEW FUNCTIONS
# from geo_utils import get_location_details, get_municipal_authority

# app = FastAPI(title="Road Condition API (Free Version)")

# @app.post("/report/incident")
# async def report_incident(
#     file: UploadFile = File(...),
#     latitude: float = Form(...),
#     longitude: float = Form(...)
# ):
#     # 1. Location Validation (Using FREE OpenStreetMap)
#     in_india, address, city = get_location_details(latitude, longitude)
    
#     if not in_india:
#         # We allow the process to fail or just warn. Here we block it.
#         raise HTTPException(status_code=400, detail=f"Location Error: {address}")

#     # 2. Process Image (Standard AI)
#     contents = await file.read()
#     nparr = np.frombuffer(contents, np.uint8)
#     frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
#     rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
#     has_damage, severity, priority, save_path = process_frame(rgb_frame, file.filename, "App Upload")
    
#     # 3. Determine Authority (Free Logic)
#     authority_name = "N/A"
#     if has_damage:
#         authority_name = get_municipal_authority(city)
    
#     # 4. Save to Database
#     insert_log("App Upload", file.filename, has_damage, severity, priority, save_path, 
#                latitude, longitude, address, authority_name)
    
#     return {
#         "status": "Reported",
#         "location": address,
#         "priority": priority,
#         "authority_notified": authority_name if has_damage else "None"
#     }
    
# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000)


import cv2
import numpy as np
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from logic import process_frame
from database import insert_log
from geo_utils import get_location_details, get_municipal_authority

app = FastAPI(title="Road Condition API (Anti-Spam)")

@app.post("/report/incident")
async def report_incident(
    file: UploadFile = File(...),
    latitude: float = Form(...),
    longitude: float = Form(...)
):
    # 1. SPAM CHECK: Reject Default/Zero Coordinates
    if latitude == 0.0 or longitude == 0.0:
        raise HTTPException(status_code=400, detail="Spam Detected: Invalid GPS Coordinates (0.0, 0.0)")

    # 2. Location Validation (Using FREE OpenStreetMap)
    in_india, address, city = get_location_details(latitude, longitude)
    
    if not in_india:
        raise HTTPException(status_code=400, detail=f"Location Error: {address}")

    # 3. Process Image
    contents = await file.read()
    
    # SPAM CHECK: Reject Empty Files
    if len(contents) == 0:
        raise HTTPException(status_code=400, detail="Spam Detected: Empty Image File")

    nparr = np.frombuffer(contents, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    # SPAM CHECK: Reject Invalid Image Formats
    if frame is None:
        raise HTTPException(status_code=400, detail="Spam Detected: Invalid/Corrupt Image Format")

    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    # "App Upload" or "Camera Upload" is determined by caller, logic stays generic
    has_damage, severity, priority, save_path = process_frame(rgb_frame, file.filename, "API Upload")
    
    # 4. Determine Authority
    authority_name = "N/A"
    if has_damage:
        authority_name = get_municipal_authority(city)
    
    # 5. Save to Database
    insert_log("API Upload", file.filename, has_damage, severity, priority, save_path, 
               latitude, longitude, address, authority_name)
    
    return {
        "status": "Reported",
        "location": address,
        "priority": priority,
        "authority_notified": authority_name if has_damage else "None"
    }
    
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)