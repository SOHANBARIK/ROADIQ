# RoadIQ 🚧🧠
**AI-Powered Road Damage Detection & Repair Priority System**  
https://roadiq.streamlit.app/
Samved – A Smart Governance Hackathon

---

## 📌 Problem Statement
Road Condition Monitoring System: automated detection, reporting, prioritization, and monitoring of road conditions (potholes, cracks) using computer vision and data analytics.

---

## ✅ Features
- Detects road damage (potholes / cracks) from image/video
- Severity estimation (Low / Medium / High)
- Priority scoring for repair planning
- Report storage + status tracking
- Admin dashboard for monitoring and analytics

---

## 🏗️ Architecture (High Level)
**User Upload (Image/Video + Location)**  
→ **FastAPI Backend**  
→ **YOLO + OpenCV Inference Service**  
→ **Database (Reports + Status)**  
→ **Dashboard (Streamlit/React)**

---

## 🛠️ Tech Stack
**AI/ML:** Python, OpenCV, YOLO (PyTorch)  
**Backend:** FastAPI  
**Dashboard:** Streamlit  
**Database:** PostgreSQL / MongoDB

---

## 📁 Project Structure
```text
RoadIQ/
│── README.md
│── frontend/
│── backend/
│── .gitignore
│── requirements.txt
