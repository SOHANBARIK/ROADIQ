# import streamlit as st
# import pandas as pd
# import sqlite3
# import numpy as np
# import requests  # <--- NEW: To talk to your Render API
# import cv2
# from datetime import datetime
# from streamlit_js_eval import get_geolocation
# from pdf_utils import generate_road_report
# from dotenv import load_dotenv
# import os

# load_dotenv()
# # --- CONFIGURATION ---
# # REPLACE THIS WITH YOUR ACTUAL RENDER URL
# API_URL = os.getenv("API_URL")

# # --- PAGE CONFIGURATION ---
# st.set_page_config(page_title="IN Road Guard", page_icon="🚧", layout="wide")

# # --- CSS ---
# st.markdown("""
#     <style>
#     .report-status { padding: 20px; border-radius: 10px; background-color: #e8f5e9; color: #2e7d32; }
#     div[data-testid="stCameraInput"] button { display: none; }
#     </style>
#     """, unsafe_allow_html=True)

# # --- NAVIGATION ---
# st.title("🇮🇳 Road Condition Monitoring System")
# tabs = st.tabs(["📊 Dashboard & Map", "📸 Report Live Incident"])

# # ==========================================
# # TAB 1: COMMAND CENTER (Reads from Local DB for Demo)
# # Note: In a real production app, this should also fetch data from an API endpoint
# # ==========================================
# with tabs[0]:
#     st.header("City-Wide Operational Overview")
#     # For now, we keep local DB reading for the dashboard view
#     # Ideally, you'd have an API endpoint like GET /incidents to populate this
#     if os.path.exists("road_monitoring.db"):
#         conn = sqlite3.connect("road_monitoring.db")
#         try:
#             df = pd.read_sql("SELECT * FROM road_logs ORDER BY id DESC", conn)
            
#             col1, col2, col3, col4 = st.columns(4)
#             with col1: st.metric("Total Scans", len(df))
#             with col2: st.metric("Critical Defects", len(df[df['priority_level'] == 'Critical']))
#             with col3: st.metric("Reports to Municipal Corp", len(df[df['damage_detected'] == 1]))
#             with col4: st.metric("Region", "India")

#             st.divider()
#             st.subheader("📍 Live Incident Map")
#             if not df.empty:
#                 map_data = df[df['damage_detected'] == 1].rename(columns={'latitude': 'lat', 'longitude': 'lon'})
#                 st.map(map_data)
#             else:
#                 st.info("No active incidents.")

#             st.subheader("📋 Municipal Reports Log")
#             for _, row in df.iterrows():
#                 with st.expander(f"{row['timestamp']} - {row['priority_level']} - {row['address']}"):
#                     st.write(f"**Authority:** {row['municipal_authority']}")
#                     # Images might need to be served via URL in production
#                     if os.path.exists(row['processed_image_path']):
#                         st.image(row['processed_image_path'], width=400)
#         finally:
#             conn.close()
#     else:
#         st.warning("Local database not found. Syncing with cloud...")

# # ==========================================
# # TAB 2: LIVE REPORTING (API CLIENT)
# # ==========================================
# with tabs[1]:
#     st.header("Report Road Damage (Live Camera Only)")
    
#     with st.container(border=True):
#         st.subheader("1. Incident Location (GPS Locked)")
#         st.info("ℹ️ Coordinates are locked to your live location.")
        
#         col_gps, col_inputs = st.columns([1, 2])
        
#         with col_gps:
#             st.write("📍 **Location Services:**")
#             loc_data = get_geolocation(component_key='my_geolocation')

#             if loc_data:
#                 new_lat = loc_data['coords']['latitude']
#                 new_lng = loc_data['coords']['longitude']
#                 if st.session_state.get('lat_input') != new_lat or st.session_state.get('lng_input') != new_lng:
#                     st.session_state['lat_input'] = new_lat
#                     st.session_state['lng_input'] = new_lng
#                     st.rerun() 
#                 st.success("✅ GPS Locked")

#         with col_inputs:
#             if 'lat_input' not in st.session_state: st.session_state['lat_input'] = 0.0000
#             if 'lng_input' not in st.session_state: st.session_state['lng_input'] = 0.0000

#             c1, c2 = st.columns(2)
#             lat = c1.number_input("Latitude", key="lat_input", format="%.6f", disabled=True)
#             lng = c2.number_input("Longitude", key="lng_input", format="%.6f", disabled=True)

#         st.subheader("2. Live Evidence")
#         camera_image = st.camera_input("Take a photo of the road damage")
        
#         if camera_image:
#             if st.button("Submit Report", type="primary"):
#                 if lat == 0.0 and lng == 0.0:
#                     st.error("⚠️ GPS Location Missing. Please click 'Get Geolocation'.")
#                 else:
#                     with st.spinner("Sending data to Cloud Server..."):
#                         try:
#                             # 1. Prepare Payload
#                             # 'camera_image' is a BytesIO object, perfect for requests
#                             files = {"file": ("capture.jpg", camera_image, "image/jpeg")}
#                             data = {"latitude": lat, "longitude": lng}
                            
#                             # 2. CALL THE RENDER API
#                             response = requests.post(API_URL, files=files, data=data)
                            
#                             if response.status_code == 200:
#                                 result = response.json()
                                
#                                 st.markdown(f'<div class="report-status">Report Filed! Priority: {result.get("priority")}</div>', unsafe_allow_html=True)
#                                 st.json(result)
                                
#                                 # 3. Generate PDF (Locally for user download)
#                                 # We construct this from the API response
#                                 report_data = {
#                                     "id": "CLOUD-ID",
#                                     "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
#                                     "address": result.get("location", "Unknown"),
#                                     "lat": lat, "lng": lng,
#                                     "authority": result.get("authority_notified", "N/A"),
#                                     "priority": result.get("priority", "N/A"),
#                                     "severity": 0.0, # Optional: Add severity to API response if needed
#                                     "image_path": "temp_cam.jpg" # Placeholder path
#                                 }
                                
#                                 # Save temp image for PDF generator
#                                 with open("temp_cam.jpg", "wb") as f:
#                                     f.write(camera_image.getbuffer())
                                    
#                                 pdf_filename = f"Report_{datetime.now().strftime('%H%M%S')}.pdf"
#                                 generate_road_report(report_data, pdf_filename)

#                                 with open(pdf_filename, "rb") as f:
#                                     st.download_button("📄 Download Official PDF Report", f, file_name=pdf_filename)
#                             else:
#                                 # Handle API Errors (e.g., Spam Detected)
#                                 error_detail = response.json().get('detail', response.text)
#                                 st.error(f"⛔ Server Error: {error_detail}")
                                
#                         except Exception as e:
#                             st.error(f"Connection Failed: {e}")





import streamlit as st
import pandas as pd
import sqlite3
import numpy as np
import requests  # To talk to your Render API
import cv2
from datetime import datetime
from streamlit_js_eval import get_geolocation
from pdf_utils import generate_road_report
from dotenv import load_dotenv
import os
from PIL import Image
import io

load_dotenv()

# --- CONFIGURATION ---
# Use Streamlit Secrets for production, fall back to os.getenv for local
# Ensure you have set API_URL in your .env file or Streamlit Cloud Secrets
API_URL = os.getenv("API_URL") 
if not API_URL and "API_URL" in st.secrets:
    API_URL = st.secrets["API_URL"]

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="IN Road Guard", page_icon="🚧", layout="wide")

# --- CSS ---
st.markdown("""
    <style>
    .report-status { padding: 20px; border-radius: 10px; background-color: #e8f5e9; color: #2e7d32; }
    /* Hide the default camera button if it still appears somehow */
    div[data-testid="stCameraInput"] button { display: none; }
    </style>
    """, unsafe_allow_html=True)

# --- NAVIGATION ---
st.title("🇮🇳 Road Condition Monitoring System")
tabs = st.tabs(["📊 Dashboard & Map", "📸 Report Live Incident"])

# ==========================================
# TAB 1: COMMAND CENTER
# ==========================================
with tabs[0]:
    st.header("City-Wide Operational Overview")
    
    if os.path.exists("road_monitoring.db"):
        conn = sqlite3.connect("road_monitoring.db")
        try:
            df = pd.read_sql("SELECT * FROM road_logs ORDER BY id DESC", conn)
            
            col1, col2, col3, col4 = st.columns(4)
            with col1: st.metric("Total Scans", len(df))
            with col2: st.metric("Critical Defects", len(df[df['priority_level'] == 'Critical']) if 'priority_level' in df.columns else 0)
            with col3: st.metric("Reports to Municipal Corp", len(df[df['damage_detected'] == 1]) if 'damage_detected' in df.columns else 0)
            with col4: st.metric("Region", "India")

            st.divider()
            st.subheader("📍 Live Incident Map")
            if not df.empty and 'damage_detected' in df.columns:
                map_data = df[df['damage_detected'] == 1].rename(columns={'latitude': 'lat', 'longitude': 'lon'})
                # Filter out invalid coordinates (0.0)
                map_data = map_data[(map_data['lat'] != 0) & (map_data['lon'] != 0)]
                st.map(map_data)
            else:
                st.info("No active incidents to map.")

            st.subheader("📋 Municipal Reports Log")
            # Only show if df has rows
            if not df.empty:
                for _, row in df.iterrows():
                    # Handle potential missing columns safely
                    p_level = row.get('priority_level', 'N/A')
                    addr = row.get('address', 'Unknown Location')
                    auth = row.get('municipal_authority', 'N/A')
                    img_path = row.get('processed_image_path', '')

                    with st.expander(f"{row.get('timestamp', 'Time N/A')} - {p_level} - {addr}"):
                        st.write(f"**Authority:** {auth}")
                        if os.path.exists(img_path):
                            st.image(img_path, width=400)
        except Exception as e:
            st.error(f"Error loading database: {e}")
        finally:
            conn.close()
    else:
        st.warning("Local database (road_monitoring.db) not found. This view shows local history.")

# ==========================================
# TAB 2: LIVE REPORTING (UPDATED FOR MOBILE)
# ==========================================
with tabs[1]:
    st.header("Report Road Damage")
    
    with st.container(border=True):
        st.subheader("1. Incident Location (GPS Locked)")
        st.info("ℹ️ Coordinates are locked to your live location.")
        
        col_gps, col_inputs = st.columns([1, 2])
        
        with col_gps:
            st.write("📍 **Location Services:**")
            # This triggers the browser permission prompt
            loc_data = get_geolocation(component_key='my_geolocation')

            if loc_data:
                new_lat = loc_data['coords']['latitude']
                new_lng = loc_data['coords']['longitude']
                
                # Update session state only if changed to prevent loops
                if st.session_state.get('lat_input') != new_lat or st.session_state.get('lng_input') != new_lng:
                    st.session_state['lat_input'] = new_lat
                    st.session_state['lng_input'] = new_lng
                    st.rerun()
                st.success("✅ GPS Locked")
            else:
                st.warning("Waiting for GPS...")

        with col_inputs:
            if 'lat_input' not in st.session_state: st.session_state['lat_input'] = 0.0000
            if 'lng_input' not in st.session_state: st.session_state['lng_input'] = 0.0000

            c1, c2 = st.columns(2)
            lat = c1.number_input("Latitude", key="lat_input", format="%.6f", disabled=True)
            lng = c2.number_input("Longitude", key="lng_input", format="%.6f", disabled=True)

        st.divider()
        st.subheader("2. Live Evidence")
        
        # --- CRITICAL CHANGE: Replaced camera_input with file_uploader ---
        # This allows mobile users to select "Take Photo" (Back Camera) or "Library"
        uploaded_file = st.file_uploader("Capture or Upload Road Image", type=['jpg', 'jpeg', 'png'])
        
        if uploaded_file is not None:
            # Display the selected image
            image = Image.open(uploaded_file)
            st.image(image, caption="Evidence Preview", use_container_width=True)

            if st.button("Submit Report", type="primary"):
                # Validate GPS before submission
                if lat == 0.0 and lng == 0.0:
                    st.error("⚠️ GPS Location Missing. Please click the 'Get Geolocation' button or wait for it to load.")
                else:
                    with st.spinner("Sending data to Cloud Server..."):
                        try:
                            # 1. Prepare Payload
                            # Reset pointer to start of file so we can read it again for the API
                            uploaded_file.seek(0)
                            
                            files = {"file": ("capture.jpg", uploaded_file, "image/jpeg")}
                            data = {"latitude": str(lat), "longitude": str(lng)}
                            
                            # 2. CALL THE RENDER API
                            if not API_URL:
                                st.error("API_URL is not set in environment variables.")
                            else:
                                response = requests.post(API_URL, files=files, data=data)
                                
                                if response.status_code == 200:
                                    result = response.json()
                                    
                                    st.markdown(f'<div class="report-status">Report Filed! Priority: {result.get("priority")}</div>', unsafe_allow_html=True)
                                    st.json(result)
                                    
                                    # 3. Generate PDF (Locally for user download)
                                    report_data = {
                                        "id": result.get("report_id", "CLOUD-ID"),
                                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                        "address": result.get("location", "Unknown"),
                                        "lat": lat, "lng": lng,
                                        "authority": result.get("authority_notified", "N/A"),
                                        "priority": result.get("priority", "N/A"),
                                        "severity": result.get("severity_score", 0.0),
                                        "image_path": "temp_cam.jpg" 
                                    }
                                    
                                    # Save temp image for PDF generator
                                    # Need to convert the uploaded PIL image back to bytes for saving
                                    image.save("temp_cam.jpg")
                                    
                                    pdf_filename = f"Report_{datetime.now().strftime('%H%M%S')}.pdf"
                                    generate_road_report(report_data, pdf_filename)

                                    with open(pdf_filename, "rb") as f:
                                        st.download_button("📄 Download Official PDF Report", f, file_name=pdf_filename, mime="application/pdf")
                                        
                                    # Clean up temp files
                                    # os.remove("temp_cam.jpg")
                                    # os.remove(pdf_filename)
                                else:
                                    # Handle API Errors
                                    try:
                                        error_detail = response.json().get('detail', response.text)
                                    except:
                                        error_detail = response.text
                                    st.error(f"⛔ Server Error: {error_detail}")
                                
                        except Exception as e:
                            st.error(f"Connection Failed: {e}")