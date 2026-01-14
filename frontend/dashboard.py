import streamlit as st
import pandas as pd
import sqlite3
import numpy as np
import requests  # <--- NEW: To talk to your Render API
import cv2
from datetime import datetime
from streamlit_js_eval import get_geolocation
from frontend.pdf_utils import generate_road_report
from dotenv import load_dotenv
import os

load_dotenv()
# --- CONFIGURATION ---
# REPLACE THIS WITH YOUR ACTUAL RENDER URL
API_URL = os.getenv("API_URL")

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="IN Road Guard", page_icon="🚧", layout="wide")

# --- CSS ---
st.markdown("""
    <style>
    .report-status { padding: 20px; border-radius: 10px; background-color: #e8f5e9; color: #2e7d32; }
    div[data-testid="stCameraInput"] button { display: none; }
    </style>
    """, unsafe_allow_html=True)

# --- NAVIGATION ---
st.title("🇮🇳 Road Condition Monitoring System")
tabs = st.tabs(["📊 Dashboard & Map", "📸 Report Live Incident"])

# ==========================================
# TAB 1: COMMAND CENTER (Reads from Local DB for Demo)
# Note: In a real production app, this should also fetch data from an API endpoint
# ==========================================
with tabs[0]:
    st.header("City-Wide Operational Overview")
    # For now, we keep local DB reading for the dashboard view
    # Ideally, you'd have an API endpoint like GET /incidents to populate this
    if os.path.exists("road_monitoring.db"):
        conn = sqlite3.connect("road_monitoring.db")
        try:
            df = pd.read_sql("SELECT * FROM road_logs ORDER BY id DESC", conn)
            
            col1, col2, col3, col4 = st.columns(4)
            with col1: st.metric("Total Scans", len(df))
            with col2: st.metric("Critical Defects", len(df[df['priority_level'] == 'Critical']))
            with col3: st.metric("Reports to Municipal Corp", len(df[df['damage_detected'] == 1]))
            with col4: st.metric("Region", "India")

            st.divider()
            st.subheader("📍 Live Incident Map")
            if not df.empty:
                map_data = df[df['damage_detected'] == 1].rename(columns={'latitude': 'lat', 'longitude': 'lon'})
                st.map(map_data)
            else:
                st.info("No active incidents.")

            st.subheader("📋 Municipal Reports Log")
            for _, row in df.iterrows():
                with st.expander(f"{row['timestamp']} - {row['priority_level']} - {row['address']}"):
                    st.write(f"**Authority:** {row['municipal_authority']}")
                    # Images might need to be served via URL in production
                    if os.path.exists(row['processed_image_path']):
                        st.image(row['processed_image_path'], width=400)
        finally:
            conn.close()
    else:
        st.warning("Local database not found. Syncing with cloud...")

# ==========================================
# TAB 2: LIVE REPORTING (API CLIENT)
# ==========================================
with tabs[1]:
    st.header("Report Road Damage (Live Camera Only)")
    
    with st.container(border=True):
        st.subheader("1. Incident Location (GPS Locked)")
        st.info("ℹ️ Coordinates are locked to your live location.")
        
        col_gps, col_inputs = st.columns([1, 2])
        
        with col_gps:
            st.write("📍 **Location Services:**")
            loc_data = get_geolocation(component_key='my_geolocation')

            if loc_data:
                new_lat = loc_data['coords']['latitude']
                new_lng = loc_data['coords']['longitude']
                if st.session_state.get('lat_input') != new_lat or st.session_state.get('lng_input') != new_lng:
                    st.session_state['lat_input'] = new_lat
                    st.session_state['lng_input'] = new_lng
                    st.rerun() 
                st.success("✅ GPS Locked")

        with col_inputs:
            if 'lat_input' not in st.session_state: st.session_state['lat_input'] = 0.0000
            if 'lng_input' not in st.session_state: st.session_state['lng_input'] = 0.0000

            c1, c2 = st.columns(2)
            lat = c1.number_input("Latitude", key="lat_input", format="%.6f", disabled=True)
            lng = c2.number_input("Longitude", key="lng_input", format="%.6f", disabled=True)

        st.subheader("2. Live Evidence")
        camera_image = st.camera_input("Take a photo of the road damage")
        
        if camera_image:
            if st.button("Submit Report", type="primary"):
                if lat == 0.0 and lng == 0.0:
                    st.error("⚠️ GPS Location Missing. Please click 'Get Geolocation'.")
                else:
                    with st.spinner("Sending data to Cloud Server..."):
                        try:
                            # 1. Prepare Payload
                            # 'camera_image' is a BytesIO object, perfect for requests
                            files = {"file": ("capture.jpg", camera_image, "image/jpeg")}
                            data = {"latitude": lat, "longitude": lng}
                            
                            # 2. CALL THE RENDER API
                            response = requests.post(API_URL, files=files, data=data)
                            
                            if response.status_code == 200:
                                result = response.json()
                                
                                st.markdown(f'<div class="report-status">Report Filed! Priority: {result.get("priority")}</div>', unsafe_allow_html=True)
                                st.json(result)
                                
                                # 3. Generate PDF (Locally for user download)
                                # We construct this from the API response
                                report_data = {
                                    "id": "CLOUD-ID",
                                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                    "address": result.get("location", "Unknown"),
                                    "lat": lat, "lng": lng,
                                    "authority": result.get("authority_notified", "N/A"),
                                    "priority": result.get("priority", "N/A"),
                                    "severity": 0.0, # Optional: Add severity to API response if needed
                                    "image_path": "temp_cam.jpg" # Placeholder path
                                }
                                
                                # Save temp image for PDF generator
                                with open("temp_cam.jpg", "wb") as f:
                                    f.write(camera_image.getbuffer())
                                    
                                pdf_filename = f"Report_{datetime.now().strftime('%H%M%S')}.pdf"
                                generate_road_report(report_data, pdf_filename)

                                with open(pdf_filename, "rb") as f:
                                    st.download_button("📄 Download Official PDF Report", f, file_name=pdf_filename)
                            else:
                                # Handle API Errors (e.g., Spam Detected)
                                error_detail = response.json().get('detail', response.text)
                                st.error(f"⛔ Server Error: {error_detail}")
                                
                        except Exception as e:
                            st.error(f"Connection Failed: {e}")