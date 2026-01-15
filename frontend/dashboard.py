import streamlit as st
import pandas as pd
import requests
import os
import uuid  # <--- NEW IMPORT for Random IDs
from datetime import datetime
from streamlit_js_eval import get_geolocation
from pdf_utils import generate_road_report
from dotenv import load_dotenv
from PIL import Image

load_dotenv()

# --- CONFIGURATION ---
API_BASE_URL = os.getenv("API_URL")
if not API_BASE_URL and "API_URL" in st.secrets:
    API_BASE_URL = st.secrets["API_URL"]

if API_BASE_URL:
    API_BASE_URL = API_BASE_URL.rstrip('/')
    REPORT_ENDPOINT = f"{API_BASE_URL}/report-incident" 
    MAP_DATA_ENDPOINT = f"{API_BASE_URL}/get-map-data"
else:
    st.error("🚨 API_URL is missing!")
    st.stop()

st.set_page_config(page_title="Road Guard", page_icon="🚧", layout="wide")

st.markdown("""
    <style>
    .report-status { padding: 20px; border-radius: 10px; background-color: #e8f5e9; color: #2e7d32; }
    div[data-testid="stCameraInput"] button { display: none; }
    </style>
    """, unsafe_allow_html=True)

st.title("Road Condition Monitoring System 🇮🇳")
tabs = st.tabs(["📊 Dashboard & Map", "📸 Report Live Incident"])

# --- TAB 1: DASHBOARD ---
with tabs[0]:
    st.header("City-Wide Operational Overview")
    try:
        response = requests.get(MAP_DATA_ENDPOINT)
        if response.status_code == 200:
            data = response.json()
            df = pd.DataFrame(data)
            if not df.empty:
                col1, col2, col3, col4 = st.columns(4)
                with col1: st.metric("Total Scans", len(df))
                with col2: st.metric("Critical Defects", len(df[df['priority'] == 'Critical']))
                with col3: st.metric("Active Reports", len(df))
                with col4: st.metric("Region", "India")
                
                st.divider()
                st.subheader("📍 Live Incident Map")
                
                df['lat'] = pd.to_numeric(df['lat'], errors='coerce')
                df['lon'] = pd.to_numeric(df['lon'], errors='coerce')
                map_data = df[(df['lat'] != 0) & (df['lon'] != 0)]
                st.map(map_data, zoom=3) # Kept zoom at 12 for better city view
                
                st.subheader("📋 Incident Log")
                
                # --- DATA TRANSFORMATION ---
                # 1. Convert Damage (0/1) to "Yes"/"No" text
                if 'damage' in df.columns:
                    df['damage'] = df['damage'].apply(lambda x: "Yes" if x else "No")

                # 2. Rename columns for display
                display_df = df.rename(columns={
                    "timestamp": "Time",
                    "priority": "Priority Level",
                    "authority": "Municipal Authority",
                    "address": "Incident Location",
                    "damage": "Damage Detected",
                    "lat": "Latitude",
                    "lon": "Longitude"
                })
                
                # 3. Define the exact order of columns
                target_cols = [
                    "Time", 
                    "Priority Level", 
                    "Damage Detected",      # Moved here for better visibility
                    "Municipal Authority", 
                    "Incident Location", 
                    "Latitude", 
                    "Longitude"
                ]
                
                # 4. Filter to ensure columns exist
                available_cols = [c for c in target_cols if c in display_df.columns]
                
                # 5. Display Table
                st.dataframe(
                    display_df[available_cols], 
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Time": st.column_config.DatetimeColumn(format="D MMM YYYY, h:mm a"),
                        "Incident Location": st.column_config.TextColumn(width="large"),
                        "Municipal Authority": st.column_config.TextColumn(width="medium"),
                        # No special config needed for "Damage Detected" since it is now just text
                    }
                )

            else:
                st.info("No incidents reported yet.")
        else:
            st.warning("Could not fetch map data.")
    except Exception as e:
        st.error(f"API Connection Error: {e}")

# --- TAB 2: REPORTING ---
with tabs[1]:
    st.header("Report Road Damage")
    with st.container(border=True):
        col_gps, col_inputs = st.columns([1, 2])
        
        with col_gps:
            st.write("📍 **Location:**")
            loc_data = get_geolocation(component_key='my_geolocation')
            if loc_data:
                new_lat = loc_data['coords']['latitude']
                new_lng = loc_data['coords']['longitude']
                if st.session_state.get('lat_input') != new_lat:
                    st.session_state['lat_input'] = new_lat
                    st.session_state['lng_input'] = new_lng
                    st.rerun()
                st.success("✅ GPS Locked")
            else:
                st.warning("Waiting for GPS...")

        with col_inputs:
            if 'lat_input' not in st.session_state: st.session_state['lat_input'] = 0.0
            if 'lng_input' not in st.session_state: st.session_state['lng_input'] = 0.0
            lat = st.session_state['lat_input']
            lng = st.session_state['lng_input']
            
            st.text(f"Coordinates:\n {lat}\n {lng}")

        st.divider()
        uploaded_file = st.file_uploader("Upload Evidence", type=['jpg', 'jpeg', 'png'])
        
        if uploaded_file is not None:
            image = Image.open(uploaded_file)
            st.image(image, caption="Preview", width=300)

            if st.button("Submit Report", type="primary"):
                if lat == 0.0:
                    st.error("⚠️ GPS Location Missing.")
                else:
                    with st.spinner("Analyzing..."):
                        try:
                            uploaded_file.seek(0)
                            files = {"file": ("capture.jpg", uploaded_file, "image/jpeg")}
                            data = {"latitude": str(lat), "longitude": str(lng)}
                            
                            response = requests.post(REPORT_ENDPOINT, files=files, data=data)
                            
                            if response.status_code == 200:
                                result = response.json()
                                priority = result.get('priority', 'N/A')
                                st.success(f"Report Filed! Priority: {priority}")
                                st.json(result)
                                
                                # --- PDF GENERATION ---
                                try:
                                    image.save("temp_cam.jpg")
                                    
                                    # --- RANDOM ID GENERATION ---
                                    random_id = uuid.uuid4().hex[:8].upper()
                                    report_id_str = f"RPT-{random_id} (Live Report)"
                                    
                                    report_data = {
                                        "id": report_id_str,  # <--- Random ID + Label
                                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                        "address": result.get("location", "Unknown"),
                                        "lat": lat, "lng": lng,
                                        "authority": result.get("authority_notified", "N/A"),
                                        "priority": priority,
                                        "severity": result.get("severity", 0.0),
                                        "image_path": "temp_cam.jpg"
                                    }
                                    
                                    pdf_filename = f"Report_{random_id}.pdf"
                                    generate_road_report(report_data, pdf_filename)
                                    
                                    with open(pdf_filename, "rb") as f:
                                        st.download_button("📄 Download PDF Report", f, file_name=pdf_filename, mime="application/pdf")
                                except Exception as e:
                                    st.error(f"PDF Generation Error: {e}")
                            else:
                                st.error(f"Server Error: {response.text}")
                        except Exception as e:
                            st.error(f"Connection Failed: {e}")