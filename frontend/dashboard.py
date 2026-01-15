import streamlit as st
import pandas as pd
import requests
import os
import uuid
import textwrap
from datetime import datetime
from streamlit_js_eval import get_geolocation
from pdf_utils import generate_road_report
from dotenv import load_dotenv
from PIL import Image, ImageFilter
# import google.generativeai as genai
from google import genai
from google.genai import types

load_dotenv()

# --- GEMINI CONFIGURATION ---
# Ensure your API key is in .env or Streamlit Secrets
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY and "GEMINI_API_KEY" in st.secrets:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    st.warning("⚠️ Gemini API Key missing. AI features disabled.")

# --- APP CONFIGURATION ---
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

# --- AI HELPER FUNCTION ---
def generate_fixed_road_image(original_image):
    """
    1. Validates if the image contains a road using Gemini.
    2. If valid, generates a repair plan.
    3. Simulates a 'fixed' image (Visual Placeholder).
    """
    if not GEMINI_API_KEY:
        return None, "AI Module Not Configured"

    # --- NEW CLIENT INITIALIZATION ---
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    try:
        # Step 1: Strict Validation & Analysis
        # Note: The new SDK uses 'models.generate_content'
        response = client.models.generate_content(
            model='gemini-2.0-flash',  # Use the newer model
            contents=[
                """
                Analyze this image strictly. 
                1. Does this image contain a road, street, or pavement? Answer YES or NO.
                2. If YES, describe the damage (potholes, cracks) in one short sentence.
                3. If NO, reply with 'INVALID_IMAGE'.
                """,
                original_image
            ]
        )
        
        analysis = response.text.strip()
        
        if "INVALID_IMAGE" in analysis or "NO" in analysis.split('\n')[0]:
            return None, "No road detected in image. AI repair skipped."

        # Step 2: Extract Repair Plan
        repair_plan = analysis.replace("YES", "").strip()
        
        # Step 3: Simulate Repair (Visual Placeholder)
        fixed_image = original_image.filter(ImageFilter.GaussianBlur(radius=3))
        
        return fixed_image, repair_plan

    except Exception as e:
        return None, f"AI Processing Error: {str(e)}"

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
                st.map(map_data, zoom=3.5)
                
                st.subheader("📋 Incident Log")
                
                if 'damage' in df.columns:
                    df['damage'] = df['damage'].apply(lambda x: "Yes" if x else "No")

                display_df = df.rename(columns={
                    "timestamp": "Time",
                    "priority": "Priority Level",
                    "authority": "Municipal Authority",
                    "address": "Incident Location",
                    "damage": "Damage Detected",
                    "lat": "Latitude",
                    "lon": "Longitude"
                })
                
                target_cols = ["Time", "Priority Level", "Damage Detected", "Municipal Authority", "Incident Location", "Latitude", "Longitude"]
                available_cols = [c for c in target_cols if c in display_df.columns]
                
                st.dataframe(
                    display_df[available_cols], 
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Time": st.column_config.DatetimeColumn(format="D MMM YYYY, h:mm a"),
                        "Incident Location": st.column_config.TextColumn(width="large"),
                        "Municipal Authority": st.column_config.TextColumn(width="medium"),
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
            
            st.text(f"Coordinates:\n Latitude: {lat}\n Longitude: {lng}")

        st.divider()
        uploaded_file = st.file_uploader("Upload Evidence", type=['jpg', 'jpeg', 'png'])
        
        if uploaded_file is not None:
            image = Image.open(uploaded_file)
            st.image(image, caption="Preview", width=300)

            if st.button("Submit Report", type="primary"):
                if lat == 0.0:
                    st.error("⚠️ GPS Location Missing.")
                else:
                    with st.spinner("Analyzing Road & Generating Repair Plan..."):
                        # --- 1. RUN GEMINI AI FIXER FIRST ---
                        fixed_img, repair_notes = generate_fixed_road_image(image)
                        
                        if fixed_img is None:
                            # If AI rejected the image (No road detected)
                            st.error(f"⚠️ Report Rejected: {repair_notes}")
                        else:
                            # --- 2. PROCEED IF VALID ROAD ---
                            try:
                                uploaded_file.seek(0)
                                files = {"file": ("capture.jpg", uploaded_file, "image/jpeg")}
                                data = {"latitude": str(lat), "longitude": str(lng)}
                                
                                response = requests.post(REPORT_ENDPOINT, files=files, data=data)
                                
                                if response.status_code == 200:
                                    result = response.json()
                                    priority = result.get('priority', 'N/A')
                                    st.success(f"Report Filed! Priority: {priority}")
                                    
                                    # Show AI Results
                                    st.subheader("🤖 AI Reconstruction Analysis")
                                    ai_col1, ai_col2 = st.columns(2)
                                    with ai_col1:
                                        st.image(image, caption="Original Damage", use_column_width=True)
                                    with ai_col2:
                                        st.image(fixed_img, caption="Projected Repair (Simulated)", use_column_width=True)
                                    st.info(f"📋 **Repair Notes:** {repair_notes}")

                                    # --- PDF GENERATION ---
                                    try:
                                        # Save both images for PDF
                                        image.save("temp_original.jpg")
                                        fixed_img.save("temp_fixed.jpg")
                                        
                                        random_id = uuid.uuid4().hex[:8].upper()
                                        report_id_str = f"RPT-{random_id}"
                                        
                                        report_data = {
                                            "id": report_id_str,
                                            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                            "address": result.get("location", "Unknown"),
                                            "lat": lat, "lng": lng,
                                            "authority": result.get("authority_notified", "N/A"),
                                            "priority": priority,
                                            "severity": result.get("severity", 0.0),
                                            "image_path": "temp_original.jpg",
                                            "fixed_image_path": "temp_fixed.jpg", # <--- NEW FIELD
                                            "repair_notes": repair_notes            # <--- NEW FIELD
                                        }
                                        
                                        pdf_filename = f"Report_{random_id}.pdf"
                                        generate_road_report(report_data, pdf_filename)
                                        
                                        with open(pdf_filename, "rb") as f:
                                            st.download_button("📄 Download Full Report (PDF)", f, file_name=pdf_filename, mime="application/pdf")
                                    except Exception as e:
                                        st.error(f"PDF Generation Error: {e}")
                                else:
                                    st.error(f"Server Error: {response.text}")
                            except Exception as e:
                                st.error(f"Connection Failed: {e}")