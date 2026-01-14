from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
from reportlab.lib import colors
import textwrap
import os

def generate_road_report(data, output_path):
    """
    Creates a professionally formatted PDF report with dynamic layout
    to prevent image overlap.
    """
    c = canvas.Canvas(output_path, pagesize=letter)
    width, height = letter  # Standard Letter size: 612w x 792h
    
    # --- STYLING CONSTANTS ---
    margin = 50
    current_y = height - 50  # Start cursor at the top
    line_height = 14
    
    # ==============================
    # 1. HEADER SECTION
    # ==============================
    # Draw a colored banner
    c.setFillColor(colors.darkblue)
    c.rect(0, current_y - 20, width, 40, fill=1, stroke=0)
    
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(margin, current_y - 10, "ROAD CONDITION REPORT")
    
    c.setFont("Helvetica", 10)
    c.drawRightString(width - margin, current_y - 10, f"Generated: {data['timestamp']}")
    
    current_y -= 60  # Move cursor down

    # ==============================
    # 2. INCIDENT DETAILS (Text)
    # ==============================
    c.setFillColor(colors.black)
    
    # Helper to draw a field
    def draw_field(label, value, y_pos):
        c.setFont("Helvetica-Bold", 11)
        c.drawString(margin, y_pos, label)
        c.setFont("Helvetica", 11)
        
        # Handle text wrapping for long addresses
        wrapped_text = textwrap.wrap(str(value), width=75) # ~75 chars fits in line
        for line in wrapped_text:
            c.drawString(margin + 120, y_pos, line)
            y_pos -= line_height
        
        return y_pos - 6 # Add extra spacing between fields

    # Draw fields and update cursor position dynamically
    current_y = draw_field("Report ID:", data['id'], current_y)
    current_y = draw_field("Status:", data['priority'], current_y)
    current_y = draw_field("Severity Score:", f"{data['severity']:.4f}", current_y)
    current_y = draw_field("Authority:", data['authority'], current_y)
    current_y = draw_field("GPS Coordinates:", f"{data['lat']}, {data['lng']}", current_y)
    current_y = draw_field("Address:", data['address'], current_y)
    
    current_y -= 20 # Add spacer before image

    # ==============================
    # 3. EVIDENCE IMAGE
    # ==============================
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin, current_y, "VISUAL EVIDENCE:")
    current_y -= 15
    
    if os.path.exists(data['image_path']):
        try:
            img = ImageReader(data['image_path'])
            img_width, img_height = img.getSize()
            
            # Calculate available space
            available_width = width - (2 * margin)
            available_height = current_y - 100 # Leave 100px for footer
            
            # Scale image to fit within the box (Preserve Aspect Ratio)
            aspect = img_height / float(img_width)
            
            display_width = available_width
            display_height = available_width * aspect
            
            # If image is too tall, scale by height instead
            if display_height > available_height:
                display_height = available_height
                display_width = display_height / aspect
            
            # Draw Image
            # Note: drawImage coords are (x, y, w, h) where y is the BOTTOM left corner
            image_bottom_y = current_y - display_height
            c.drawImage(img, margin, image_bottom_y, width=display_width, height=display_height, mask='auto')
            
            # Draw a border around the image
            c.setStrokeColor(colors.gray)
            c.rect(margin, image_bottom_y, display_width, display_height, fill=0)
            
        except Exception as e:
            c.setFillColor(colors.red)
            c.drawString(margin, current_y - 20, f"Error loading image: {e}")
    else:
        c.setFillColor(colors.gray)
        c.rect(margin, current_y - 200, 400, 200, fill=0)
        c.drawString(margin + 10, current_y - 100, "No Image Available")

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