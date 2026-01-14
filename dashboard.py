import streamlit as st
import pandas as pd
import sqlite3
import cv2
import numpy as np
import os
from datetime import datetime
from streamlit_js_eval import get_geolocation

# --- SYSTEM COMPONENTS ---
from logic import process_frame
from database import insert_log
from geo_utils import get_location_details, get_municipal_authority
from pdf_utils import generate_road_report

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="IN Road Guard", page_icon="🚧", layout="wide")

# --- CSS ---
st.markdown("""
    <style>
    .report-status { padding: 20px; border-radius: 10px; background-color: #e8f5e9; color: #2e7d32; }
    /* Hide the default "Stop" button in camera input to make it cleaner */
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
                if os.path.exists(row['processed_image_path']):
                    st.image(row['processed_image_path'], width=400)
    finally:
        conn.close()

# ==========================================
# TAB 2: LIVE REPORTING (LOCKED & SECURE)
# ==========================================
with tabs[1]:
    st.header("Report Road Damage (Live Camera Only)")
    
    with st.container(border=True):
        st.subheader("1. Incident Location (GPS Locked)")
        st.info("ℹ️ Coordinates are locked to your live location to prevent data tampering.")
        
        col_gps, col_inputs = st.columns([1, 2])
        
        # --- GPS LOGIC ---
        with col_gps:
            st.write("📍 **Location Services:**")
            
            # This creates the button "Get Geolocation"
            loc_data = get_geolocation(component_key='my_geolocation')

            if loc_data:
                new_lat = loc_data['coords']['latitude']
                new_lng = loc_data['coords']['longitude']
                
                # Update Session State if new data arrives
                if st.session_state.get('lat_input') != new_lat or st.session_state.get('lng_input') != new_lng:
                    st.session_state['lat_input'] = new_lat
                    st.session_state['lng_input'] = new_lng
                    st.rerun() 

                st.success("✅ GPS Locked")

        with col_inputs:
            # Initialize Session State
            if 'lat_input' not in st.session_state: st.session_state['lat_input'] = 0.0000
            if 'lng_input' not in st.session_state: st.session_state['lng_input'] = 0.0000

            c1, c2 = st.columns(2)
            
            # --- SECURITY FEATURE: DISABLED INPUTS ---
            # 'disabled=True' prevents the user from typing fake coordinates.
            # They can ONLY be updated by the GPS button via session_state.
            lat = c1.number_input("Latitude", key="lat_input", format="%.6f", disabled=True)
            lng = c2.number_input("Longitude", key="lng_input", format="%.6f", disabled=True)

        st.subheader("2. Live Evidence")
        
        # --- SECURITY FEATURE: CAMERA INPUT ONLY ---
        # Forces the user to take a picture RIGHT NOW. No file upload allowed.
        camera_image = st.camera_input("Take a photo of the road damage")
        
        if camera_image:
            # Optional: Add a small delay/spinner or just a submit button
            if st.button("Submit Report", type="primary"):
                # Validation: GPS must be locked (non-zero)
                if lat == 0.0 and lng == 0.0:
                    st.error("⚠️ GPS Location Missing. Please click 'Get Geolocation'.")
                else:
                    with st.spinner("Analyzing Live Capture..."):
                        # Process the camera buffer directly
                        file_bytes = np.asarray(bytearray(camera_image.read()), dtype=np.uint8)
                        frame = cv2.imdecode(file_bytes, 1)
                        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                        # Geo & AI Logic
                        in_india, address, city = get_location_details(lat, lng)
                        
                        if not in_india:
                            st.error(f"Operation restricted to India. Current location: {address}")
                        else:
                            # Generate a unique filename for the capture
                            filename = f"cam_{datetime.now().strftime('%H%M%S')}.jpg"
                            
                            has_damage, severity, priority, saved_path = process_frame(rgb_frame, filename)
                            authority = get_municipal_authority(city) if has_damage else "N/A"

                            insert_log("Live Camera", filename, has_damage, severity, priority, 
                                       saved_path, lat, lng, address, authority)

                            st.markdown(f'<div class="report-status">Report Successfully Filed! Status: {priority}</div>', unsafe_allow_html=True)
                            
                            # JSON Summary
                            st.json({
                                "status": "Reported",
                                "location": address,
                                "priority": priority,
                                "authority_notified": authority
                            })

                            # PDF Report Generation
                            report_data = {
                                "id": "LIVE-CAM",
                                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "address": address,
                                "lat": lat, "lng": lng,
                                "authority": authority,
                                "priority": priority,
                                "severity": severity,
                                "image_path": saved_path
                            }
                            pdf_filename = f"Report_{datetime.now().strftime('%H%M%S')}.pdf"
                            generate_road_report(report_data, pdf_filename)

                            with open(pdf_filename, "rb") as f:
                                st.download_button(
                                    label="📄 Download Official PDF Report",
                                    data=f,
                                    file_name=pdf_filename,
                                    mime="application/pdf"
                                )