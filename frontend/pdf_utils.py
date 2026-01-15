from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors
import textwrap
import os

def generate_road_report(data, output_path):
    """
    Creates a professionally formatted PDF report with dynamic layout.
    Includes Side-by-Side comparison for AI Road Fixes.
    """
    c = canvas.Canvas(output_path, pagesize=letter)
    width, height = letter  # Standard Letter size: 612w x 792h
    
    # --- STYLING CONSTANTS ---
    margin = 50
    current_y = height - 50 
    line_height = 14
    
    # ==============================
    # 1. HEADER SECTION
    # ==============================
    c.setFillColor(colors.darkblue)
    c.rect(0, current_y - 20, width, 40, fill=1, stroke=0)
    
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(margin, current_y - 10, "ROAD CONDITION REPORT")
    
    c.setFont("Helvetica", 10)
    c.drawRightString(width - margin, current_y - 10, f"Generated: {data['timestamp']}")
    
    current_y -= 60

    # ==============================
    # 2. INCIDENT DETAILS
    # ==============================
    c.setFillColor(colors.black)
    
    def draw_field(label, value, y_pos):
        c.setFont("Helvetica-Bold", 11)
        c.drawString(margin, y_pos, label)
        c.setFont("Helvetica", 11)
        
        wrapped_text = textwrap.wrap(str(value), width=75)
        for line in wrapped_text:
            c.drawString(margin + 120, y_pos, line)
            y_pos -= line_height
        
        return y_pos - 6 

    current_y = draw_field("Report ID:", data['id'], current_y)
    current_y = draw_field("Status:", data['priority'], current_y)
    current_y = draw_field("Severity Score:", f"{data['severity']:.4f}", current_y)
    current_y = draw_field("Authority:", data['authority'], current_y)
    current_y = draw_field("GPS Coordinates:", f"{data['lat']}, {data['lng']}", current_y)
    current_y = draw_field("Address:", data['address'], current_y)
    
    # Add AI Repair Notes
    if 'repair_notes' in data:
        current_y = draw_field("AI Repair Plan:", data['repair_notes'], current_y)
    
    current_y -= 20 

    # ==============================
    # 3. VISUAL EVIDENCE (Comparison)
    # ==============================
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin, current_y, "AI RECONSTRUCTION ANALYSIS:")
    current_y -= 25
    
    # Calculate dimensions for side-by-side images
    available_width = width - (2 * margin)
    img_display_width = (available_width / 2) - 10 # Split width minus gap
    img_display_height = 200 # Fixed height for consistency
    
    # -- Draw ORIGINAL Image (Left) --
    if os.path.exists(data['image_path']):
        try:
            img = ImageReader(data['image_path'])
            c.drawImage(img, margin, current_y - img_display_height, width=img_display_width, height=img_display_height, mask='auto')
            
            c.setFont("Helvetica-Bold", 10)
            c.drawString(margin, current_y - img_display_height - 15, "ORIGINAL DAMAGE")
        except Exception as e:
            c.drawString(margin, current_y - 50, f"Img Error: {e}")
            
    # -- Draw FIXED Image (Right) --
    if 'fixed_image_path' in data and os.path.exists(data['fixed_image_path']):
        try:
            img_fix = ImageReader(data['fixed_image_path'])
            x_pos = margin + img_display_width + 20
            c.drawImage(img_fix, x_pos, current_y - img_display_height, width=img_display_width, height=img_display_height, mask='auto')
            
            c.setFont("Helvetica-Bold", 10)
            c.drawString(x_pos, current_y - img_display_height - 15, "AI PROJECTED REPAIR")
        except Exception as e:
             pass

    # ==============================
    # 4. FOOTER
    # ==============================
    c.setStrokeColor(colors.lightgrey)
    c.line(margin, 50, width - margin, 50)
    c.setFillColor(colors.darkgray)
    c.setFont("Helvetica", 8)
    c.drawString(margin, 35, "RoadGuard AI System | Automated Municipal Reporting")
    c.drawRightString(width - margin, 35, "Page 1 of 1")

    c.save()