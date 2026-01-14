# import cv2
# import numpy as np
# import os
# from ultralytics import YOLO

# # --- UPDATE 1: Path Safety ---
# # This ensures we find the model even if you run the script from a different terminal path
# BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# MODEL_PATH = os.path.join(BASE_DIR, 'best.pt')
# OUTPUT_DIR = os.path.join(BASE_DIR, 'processed_images')

# # Create the output directory if it doesn't exist
# os.makedirs(OUTPUT_DIR, exist_ok=True)

# # Load model
# if not os.path.exists(MODEL_PATH):
#     print(f"⚠️ ERROR: Model file not found at {MODEL_PATH}")
#     print("Please make sure 'best.pt' is in the same folder as this script.")
#     # Fallback to standard model so code doesn't crash during testing, or raise error
#     model = YOLO('yolov8n.pt') 
# else:
#     print(f"✅ Loading Custom Model: {MODEL_PATH}")
#     model = YOLO(MODEL_PATH)

# def preprocess_image(image_array):
#     """
#     Flowchart: Image Preprocessing (Resize, Noise Removal)
#     """
#     # 1. Resize (standardize input to 640x640 for consistency)
#     # Note: This might squash wide images, but ensures consistent area calculations
#     resized = cv2.resize(image_array, (640, 640))
    
#     # 2. Noise Removal (Gaussian Blur)
#     # This helps reduce false positives in texture-heavy road surfaces
#     blurred = cv2.GaussianBlur(resized, (5, 5), 0)
    
#     return blurred

# def calculate_severity(detections, img_area):
#     """
#     Flowchart: Calculate Severity Level -> Prioritize Road Repair
#     """
#     damage_area = 0
#     for box in detections:
#         x1, y1, x2, y2 = box.xyxy[0].tolist()
#         width = x2 - x1
#         height = y2 - y1
#         damage_area += (width * height)

#     severity_score = damage_area / img_area
    
#     # Prioritization Logic
#     if severity_score > 0.15: # >15% of road is damaged
#         return "Critical", severity_score, (0, 0, 255) # Red
#     elif severity_score > 0.05:
#         return "High", severity_score, (0, 165, 255)   # Orange
#     elif severity_score > 0:
#         return "Medium", severity_score, (0, 255, 255) # Yellow
#     else:
#         return "Low", 0.0, (0, 255, 0) # Green

# def process_frame(frame, filename, source_type="Image"):
#     """
#     Orchestrates the detection flow for a single frame.
#     """
#     # 1. Preprocess
#     clean_frame = preprocess_image(frame)
#     h, w, _ = clean_frame.shape
    
#     # 2. Inference
#     results = model(clean_frame, verbose=False)
#     detections = results[0].boxes
    
#     # 3. Detect Damage Logic
#     has_damage = len(detections) > 0
    
#     # Default values
#     priority = "Safe"
#     severity = 0.0
#     color = (0, 255, 0) # Green by default

#     if has_damage:
#         priority, severity, color = calculate_severity(detections, w * h)
        
#         # Draw bounding boxes for "Processed Image"
#         for box in detections:
#             x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            
#             # Draw Box
#             cv2.rectangle(clean_frame, (x1, y1), (x2, y2), color, 2)
            
#             # Draw Label Background
#             label = f"{priority} ({int(box.conf[0]*100)}%)"
#             (w_text, h_text), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
#             cv2.rectangle(clean_frame, (x1, y1 - 20), (x1 + w_text, y1), color, -1)
            
#             # Draw Text
#             cv2.putText(clean_frame, label, (x1, y1 - 5), 
#                         cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

#     # --- UPDATE 2: Save to 'processed_images' folder ---
#     # Construct full path to save
#     save_path = os.path.join(OUTPUT_DIR, f"processed_{filename}")
    
#     # Convert RGB back to BGR for OpenCV saving
#     cv2.imwrite(save_path, cv2.cvtColor(clean_frame, cv2.COLOR_RGB2BGR))
    
#     return has_damage, severity, priority, save_path





import cv2
import base64
import os
import time
from typing import TypedDict, Literal
from ultralytics import YOLO
from dotenv import load_dotenv

# --- LANGGRAPH & LANGCHAIN IMPORTS ---
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

load_dotenv()

# --- CONFIGURATION ---
# Replace with your actual key or set os.environ["GOOGLE_API_KEY"]
API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError("GOOGLE_API_KEY is missing. Check your .env file.")


# Initialize the Vision LLM (The Judge)
llm_judge = ChatGoogleGenerativeAI(
    model="gemini-1.5-flash",
    google_api_key=API_KEY,
    temperature=0
)

# Load the "Tool" (Your Pothole Model)
pothole_model = YOLO('best.pt') 

# --- HELPER: Convert OpenCV Image to Base64 ---
def encode_image(image_array):
    # Convert RGB to BGR for OpenCV encoding
    bgr_image = cv2.cvtColor(image_array, cv2.COLOR_RGB2BGR)
    _, buffer = cv2.imencode('.jpg', bgr_image)
    return base64.b64encode(buffer).decode('utf-8')

# --- 1. DEFINE GRAPH STATE ---
class AgentState(TypedDict):
    image:  object        # The raw numpy image
    filename: str         # The filename
    is_road: bool         # The LLM's verdict
    final_output: dict    # The final results to return

# --- 2. DEFINE NODES ---

def node_judge_image(state: AgentState):
    """
    The LLM looks at the image and decides if it's a road.
    """
    print("🤖 Agent: Judging image content...")
    img_base64 = encode_image(state["image"])
    
    # Prompt for the Vision Model
    message = HumanMessage(
        content=[
            {"type": "text", "text": "Look at this image. Is this an image of a road, street, highway, or pavement? Answer strictly with 'YES' or 'NO'."},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_base64}"}}
        ]
    )
    
    response = llm_judge.invoke([message])
    decision = response.content.strip().upper()
    
    print(f"🤖 Agent Verdict: {decision}")
    
    # Update State
    return {"is_road": "YES" in decision}

def node_detect_damage(state: AgentState):
    """
    The 'Tool' (YOLO) runs only if the image is valid.
    """
    print("🛠️ Tool: Scanning for potholes...")
    frame = state["image"]
    filename = state["filename"]
    
    results = pothole_model(frame)
    
    has_damage = False
    max_conf = 0.0
    
    # Parse YOLO results
    for r in results:
        if len(r.boxes) > 0:
            has_damage = True
            conf_scores = r.boxes.conf.cpu().numpy()
            if len(conf_scores) > 0:
                max_conf = float(max(conf_scores))
    
    # Priority Logic
    priority = "Safe"
    if has_damage:
        if max_conf > 0.8: priority = "Critical"
        elif max_conf > 0.5: priority = "High"
        else: priority = "Medium"

    # Save Image
    output_dir = "processed_images"
    os.makedirs(output_dir, exist_ok=True)
    annotated_frame = results[0].plot()
    timestamp = int(time.time())
    save_path = os.path.join(output_dir, f"proc_{timestamp}_{filename}")
    
    # Convert back to BGR for saving
    save_img = cv2.cvtColor(annotated_frame, cv2.COLOR_RGB2BGR)
    cv2.imwrite(save_path, save_img)
    
    return {
        "final_output": {
            "has_damage": has_damage,
            "severity": max_conf,
            "priority": priority,
            "save_path": save_path
        }
    }

def node_reject_spam(state: AgentState):
    """
    Handles non-road images.
    """
    print("⛔ Agent: Rejection Protocol Initiated.")
    # We raise an error that the Dashboard will catch
    raise ValueError("Spam Detected: The AI Judge determined this is NOT a road image.")

# --- 3. BUILD THE GRAPH ---
workflow = StateGraph(AgentState)

# Add Nodes
workflow.add_node("judge", node_judge_image)
workflow.add_node("detector", node_detect_damage)
workflow.add_node("reject", node_reject_spam)

# Add Conditional Edges (The Router)
def router(state: AgentState):
    if state["is_road"]:
        return "detector"
    else:
        return "reject"

workflow.set_entry_point("judge")
workflow.add_conditional_edges("judge", router)
workflow.add_edge("detector", END)
workflow.add_edge("reject", END)

# Compile
app = workflow.compile()

# --- 4. EXPOSED FUNCTION (API/DASHBOARD CALLS THIS) ---
def process_frame(rgb_frame, filename_str, source="Web"):
    """
    Entry point that invokes the LangGraph Agent.
    """
    try:
        # Run the Graph
        result = app.invoke({"image": rgb_frame, "filename": filename_str})
        
        # Extract results
        out = result["final_output"]
        return out["has_damage"], out["severity"], out["priority"], out["save_path"]
        
    except ValueError as e:
        # Re-raise the spam error so dashboard shows the red box
        raise e
    except Exception as e:
        print(f"Graph Error: {e}")
        # Fallback in case of API errors (allow it but log it)
        return False, 0.0, "Error", ""