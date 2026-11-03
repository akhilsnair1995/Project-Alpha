"""
SVG Blueprint Generator for Project Alpha: Wall-E Autonomous Rover & Charging Dock.
Generates 1:1 scale laser-ready SVGs with all holes, slots, notches, and cutouts.
Red (#FF0000) stroke = Vector Through-Cut
Blue (#0000FF) stroke = Vector Score / Engrave
"""

import math
import os

def create_svg_element(tag, **attrs):
    attr_str = " ".join(f'{k}="{v}"' for k, v in attrs.items())
    return f"<{tag} {attr_str} />"

class SVGSheet:
    def __init__(self, width_mm, height_mm, title="Laser Cut Sheet"):
        self.width = width_mm
        self.height = height_mm
        self.title = title
        self.elements = []

    def rect(self, x, y, w, h, rx=0, ry=0, color="#FF0000", stroke_width=0.1):
        self.elements.append(
            f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" '
            f'rx="{rx:.2f}" ry="{ry:.2f}" fill="none" stroke="{color}" stroke-width="{stroke_width}" />'
        )

    def circle(self, cx, cy, r, color="#FF0000", stroke_width=0.1):
        self.elements.append(
            f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r:.2f}" '
            f'fill="none" stroke="{color}" stroke-width="{stroke_width}" />'
        )

    def text(self, x, y, text, size=3.0, color="#0000FF"):
        self.elements.append(
            f'<text x="{x:.2f}" y="{y:.2f}" font-family="Arial, sans-serif" '
            f'font-size="{size:.2f}mm" fill="{color}">{text}</text>'
        )

    def to_svg(self):
        header = (
            f'<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n'
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{self.width}mm" height="{self.height}mm" '
            f'viewBox="0 0 {self.width} {self.height}">\n'
            f'<!-- {self.title} - 1:1 Scale Millimeter Precision -->\n'
        )
        body = "\n".join(f"  {el}" for el in self.elements)
        footer = "\n</svg>\n"
        return header + body + footer

def generate_chassis_sheet():
    # Sheet size: 400mm x 300mm (standard 3mm acrylic sheet)
    sheet = SVGSheet(420, 297, "Project Alpha - Wall-E Complete Chassis Cut-Sheet")
    
    # Global stroke settings
    CUT = "#FF0000"
    ENGRAVE = "#0000FF"
    
    # -------------------------------------------------------------
    # 1. BOTTOM BASE PLATE (100mm x 100mm) at (10, 10)
    # -------------------------------------------------------------
    x0, y0 = 10, 10
    sheet.text(x0 + 2, y0 + 6, "1. BOTTOM BASE PLATE (100x100mm)", 2.5, ENGRAVE)
    sheet.rect(x0, y0, 100, 100, 2, 2, CUT)
    # 4x M3 Corner Standoff Holes (5mm offset -> spacing 90x90mm)
    for dx, dy in [(5, 5), (95, 5), (5, 95), (95, 95)]:
        sheet.circle(x0 + dx, y0 + dy, 1.6, CUT)  # 3.2mm diam
    # 2x Underside Charging Contactor Holes (30mm apart, 20mm from rear edge)
    sheet.circle(x0 + 35, y0 + 80, 1.6, CUT)  # Left contact (+)
    sheet.circle(x0 + 65, y0 + 80, 1.6, CUT)  # Right contact (-)
    sheet.text(x0 + 31, y0 + 75, "+ CHARGE -", 2.0, ENGRAVE)
    # 2x Cliff Sensor Slots on Front (TCRT5000)
    sheet.rect(x0 + 8, y0 + 4, 10, 6, 1, 1, CUT)
    sheet.circle(x0 + 13, y0 + 14, 1.6, CUT) # Mount screw
    sheet.rect(x0 + 82, y0 + 4, 10, 6, 1, 1, CUT)
    sheet.circle(x0 + 87, y0 + 14, 1.6, CUT) # Mount screw
    # 4x N20 / Track Mounting Slots
    sheet.rect(x0 + 20, y0 + 35, 12, 3.2, 1.6, 1.6, CUT)
    sheet.rect(x0 + 20, y0 + 60, 12, 3.2, 1.6, 1.6, CUT)
    sheet.rect(x0 + 68, y0 + 35, 12, 3.2, 1.6, 1.6, CUT)
    sheet.rect(x0 + 68, y0 + 60, 12, 3.2, 1.6, 1.6, CUT)

    # -------------------------------------------------------------
    # 2. SEPARATOR DECK / MID-TRAY (94mm x 94mm) at (120, 10)
    # -------------------------------------------------------------
    x0, y0 = 120, 10
    sheet.text(x0 + 2, y0 + 6, "2. MID-DECK TRAY (94x94mm)", 2.5, ENGRAVE)
    sheet.rect(x0, y0, 94, 94, 2, 2, CUT)
    # 4x M3 Standoff Holes (offset 2mm from edge -> spacing 90x90mm, aligns with base)
    for dx, dy in [(2, 2), (92, 2), (2, 92), (92, 92)]:
        sheet.circle(x0 + dx, y0 + dy, 1.6, CUT)
    # 4x M2.5 Raspberry Pi 4 Holes (58mm length x 49mm width centered at x=47, y=47)
    pi_cx, pi_cy = x0 + 47, y0 + 47
    for dx in [-29, 29]:
        for dy in [-24.5, 24.5]:
            sheet.circle(pi_cx + dx, pi_cy + dy, 1.35, CUT) # 2.7mm diam
    sheet.text(pi_cx - 15, pi_cy - 10, "Raspberry Pi 4", 2.2, ENGRAVE)
    # Central Cable Pass-Through Slot
    sheet.rect(pi_cx - 12, pi_cy + 5, 24, 10, 3, 3, CUT)

    # -------------------------------------------------------------
    # 3. TOP LID PLATE (100mm x 100mm) at (225, 10)
    # -------------------------------------------------------------
    x0, y0 = 225, 10
    sheet.text(x0 + 2, y0 + 6, "3. TOP LID (100x100mm)", 2.5, ENGRAVE)
    sheet.rect(x0, y0, 100, 100, 2, 2, CUT)
    # 4x M3 Corner Standoff Holes
    for dx, dy in [(5, 5), (95, 5), (5, 95), (95, 95)]:
        sheet.circle(x0 + dx, y0 + dy, 1.6, CUT)
    # Center Pan Servo Cutout (MG90S: 23.5mm x 12.5mm centered at x=50, y=50)
    sheet.rect(x0 + 50 - 11.75, y0 + 50 - 6.25, 23.5, 12.5, 0.5, 0.5, CUT)
    # 2x MG90S Mounting Ear Holes (2.2mm diam, 28mm spacing along X axis)
    sheet.circle(x0 + 50 - 14, y0 + 50, 1.1, CUT)
    sheet.circle(x0 + 50 + 14, y0 + 50, 1.1, CUT)
    # Cable Slots for Dual Displays & Camera Ribbon
    sheet.rect(x0 + 25, y0 + 75, 20, 6, 2, 2, CUT) # Display wires
    sheet.rect(x0 + 55, y0 + 75, 20, 6, 2, 2, CUT) # CSI Ribbon
    # TTP223 Touch Sensor Mounting Holes
    sheet.circle(x0 + 80, y0 + 25, 1.1, CUT)
    sheet.circle(x0 + 90, y0 + 25, 1.1, CUT)
    sheet.text(x0 + 75, y0 + 20, "TOUCH", 2.0, ENGRAVE)

    # -------------------------------------------------------------
    # 4. BINOCULAR HEAD FACEPLATE (96mm x 46mm) at (10, 120)
    # -------------------------------------------------------------
    x0, y0 = 10, 120
    sheet.text(x0 + 2, y0 + 6, "4. BINOCULAR HEAD (96x46mm)", 2.5, ENGRAVE)
    sheet.rect(x0, y0, 96, 46, 4, 4, CUT)
    # Left Eye Cutout (1.28" Round LCD: 33.5mm diam, centered at x=23, y=24)
    lex, ley = x0 + 23, y0 + 24
    sheet.circle(lex, ley, 16.75, CUT)
    # 4x M2 Mount holes for Left LCD (36mm x 36mm pattern)
    for dx in [-18, 18]:
        for dy in [-18, 18]:
            sheet.circle(lex + dx, ley + dy, 1.1, CUT)
    sheet.text(lex - 7, ley + 1, "LEFT EYE", 2.0, ENGRAVE)
    
    # Right Eye Cutout (1.28" Round LCD: 33.5mm diam, centered at x=73, y=24)
    rex, rey = x0 + 73, y0 + 24
    sheet.circle(rex, rey, 16.75, CUT)
    # 4x M2 Mount holes for Right LCD (36mm x 36mm pattern)
    for dx in [-18, 18]:
        for dy in [-18, 18]:
            sheet.circle(rex + dx, rey + dy, 1.1, CUT)
    sheet.text(rex - 8, rey + 1, "RIGHT EYE", 2.0, ENGRAVE)

    # Center Bridge Camera Cutout (9.0mm diam lens hole at x=48, y=24)
    cam_x, cam_y = x0 + 48, y0 + 24
    sheet.circle(cam_x, cam_y, 4.5, CUT) # 9mm lens hole
    # 4x M2 Camera V2 PCB Mount Holes (21mm horiz x 12.5mm vert spacing)
    for dx in [-10.5, 10.5]:
        for dy in [-6.25, 6.25]:
            sheet.circle(cam_x + dx, cam_y + dy, 1.1, CUT)
    sheet.text(cam_x - 5, cam_y - 8, "CAM", 2.0, ENGRAVE)
    # 2x Tilt Bracket Connection Holes at bottom
    sheet.circle(cam_x - 8, y0 + 41, 1.1, CUT)
    sheet.circle(cam_x + 8, y0 + 41, 1.1, CUT)

    # -------------------------------------------------------------
    # 5. DUAL EYEBROW VISORS (45mm x 18mm each) at (115, 120)
    # -------------------------------------------------------------
    for i, label in enumerate(["5A. LEFT BROW", "5B. RIGHT BROW"]):
        bx, by = 115 + i * 50, 120
        sheet.text(bx + 2, by + 5, label, 2.0, ENGRAVE)
        sheet.rect(bx, by, 45, 18, 2, 2, CUT)
        # 2x M2 holes to bolt to top of eye
        sheet.circle(bx + 10, by + 14, 1.1, CUT)
        sheet.circle(bx + 35, by + 14, 1.1, CUT)

    # -------------------------------------------------------------
    # 6. FRONT CHEST PLATE (100mm x 85mm) at (10, 175)
    # -------------------------------------------------------------
    x0, y0 = 10, 175
    sheet.text(x0 + 2, y0 + 6, "6. FRONT CHEST (100x85mm)", 2.5, ENGRAVE)
    sheet.rect(x0, y0, 100, 85, 2, 2, CUT)
    # 4x M3 Corner Standoff Holes
    for dx, dy in [(5, 5), (95, 5), (5, 80), (95, 80)]:
        sheet.circle(x0 + dx, y0 + dy, 1.6, CUT)
    # VL53L0X ToF Laser Sensor Cutout (18mm x 8mm) at Center
    sheet.rect(x0 + 50 - 9, y0 + 35, 18, 8, 1, 1, CUT)
    sheet.circle(x0 + 50 - 13, y0 + 39, 1.1, CUT) # M2 screw
    sheet.circle(x0 + 50 + 13, y0 + 39, 1.1, CUT) # M2 screw
    sheet.text(x0 + 42, y0 + 32, "LASER ToF", 2.0, ENGRAVE)
    # INMP441 Microphone Port (3.2mm hole)
    sheet.circle(x0 + 25, y0 + 55, 1.6, CUT)
    sheet.circle(x0 + 20, y0 + 55, 1.1, CUT) # M2 mount
    sheet.circle(x0 + 30, y0 + 55, 1.1, CUT) # M2 mount
    sheet.text(x0 + 22, y0 + 50, "MIC", 2.0, ENGRAVE)
    # Solar Gauge Decorative Slot (30mm x 8mm)
    sheet.rect(x0 + 55, y0 + 52, 32, 7, 1.5, 1.5, CUT)
    sheet.text(x0 + 57, y0 + 49, "SOLAR LEVEL", 1.8, ENGRAVE)

    # -------------------------------------------------------------
    # 7. REAR ACCESS PLATE (100mm x 85mm) at (120, 175)
    # -------------------------------------------------------------
    x0, y0 = 120, 175
    sheet.text(x0 + 2, y0 + 6, "7. REAR ACCESS (100x85mm)", 2.5, ENGRAVE)
    sheet.rect(x0, y0, 100, 85, 2, 2, CUT)
    # 4x M3 Corner Standoff Holes
    for dx, dy in [(5, 5), (95, 5), (5, 80), (95, 80)]:
        sheet.circle(x0 + dx, y0 + dy, 1.6, CUT)
    # KCD11 Rocker Switch Cutout (19.2mm x 12.9mm)
    sheet.rect(x0 + 20, y0 + 30, 19.5, 13.0, 0.5, 0.5, CUT)
    sheet.text(x0 + 22, y0 + 26, "POWER", 2.0, ENGRAVE)
    # USB-C Charging Port Breakout (9.5mm x 4.0mm) + 2x M2 holes
    sheet.rect(x0 + 60, y0 + 35, 10.0, 4.2, 1.5, 1.5, CUT)
    sheet.circle(x0 + 55, y0 + 37, 1.1, CUT)
    sheet.circle(x0 + 75, y0 + 37, 1.1, CUT)
    sheet.text(x0 + 58, y0 + 31, "TYPE-C", 2.0, ENGRAVE)
    # SIM Card / MicroSD Service Inspection Slot (25mm x 12mm)
    sheet.rect(x0 + 38, y0 + 55, 25.0, 12.0, 2.0, 2.0, CUT)
    sheet.text(x0 + 40, y0 + 52, "SIM / SD", 2.0, ENGRAVE)

    # -------------------------------------------------------------
    # 8. LEFT & RIGHT SIDE VENT PANELS (94mm x 85mm each) at (230, 120) & (230, 210)
    # -------------------------------------------------------------
    for i, label in enumerate(["8A. LEFT SIDE", "8B. RIGHT SIDE"]):
        sx, sy = 230, 120 + i * 88
        sheet.text(sx + 2, sy + 6, f"{label} (94x85mm)", 2.2, ENGRAVE)
        sheet.rect(sx, sy, 94, 85, 2, 2, CUT)
        # 4x M3 Corner Holes (matching mid-tray offset)
        for dx, dy in [(2, 5), (92, 5), (2, 80), (92, 80)]:
            sheet.circle(sx + dx, sy + dy, 1.6, CUT)
        # Ventilation Airflow Grid (3mm cooling holes for Pi 4)
        for col in range(5):
            for row in range(4):
                sheet.circle(sx + 35 + col * 6, sy + 35 + row * 6, 1.5, CUT)
        sheet.text(sx + 35, sy + 30, "AIR VENT", 1.8, ENGRAVE)

    return sheet.to_svg()

def generate_dock_sheet():
    # Sheet for Charging Dock (300mm x 200mm)
    sheet = SVGSheet(300, 200, "Project Alpha - Wall-E Charging Dock Cut-Sheet")
    CUT = "#FF0000"
    ENGRAVE = "#0000FF"

    # 1. Dock Floor Plate (120mm x 140mm)
    x0, y0 = 10, 10
    sheet.text(x0 + 2, y0 + 6, "1. DOCK FLOOR RAMP (120x140mm)", 2.5, ENGRAVE)
    sheet.rect(x0, y0, 120, 140, 2, 2, CUT)
    # 4x M3 Base Mounting / Rubber Foot Holes
    for dx, dy in [(6, 6), (114, 6), (6, 134), (114, 134)]:
        sheet.circle(x0 + dx, y0 + dy, 1.6, CUT)
    # Two Spring Contact Plate Cutouts / Screw Mounts (30mm spacing)
    # Left (+) contact rail: 15mm x 50mm
    sheet.rect(x0 + 40, y0 + 65, 15, 50, 2, 2, CUT)
    sheet.circle(x0 + 47.5, y0 + 58, 1.6, CUT) # (+) terminal screw
    sheet.text(x0 + 44, y0 + 54, "+", 3.0, ENGRAVE)
    # Right (-) contact rail: 15mm x 50mm
    sheet.rect(x0 + 65, y0 + 65, 15, 50, 2, 2, CUT)
    sheet.circle(x0 + 72.5, y0 + 58, 1.6, CUT) # (-) terminal screw
    sheet.text(x0 + 70, y0 + 54, "-", 3.0, ENGRAVE)
    sheet.text(x0 + 42, y0 + 125, "ROBOT ENTERS", 2.0, ENGRAVE)

    # 2. Dock Backboard (120mm x 80mm) at (140, 10)
    x0, y0 = 140, 10
    sheet.text(x0 + 2, y0 + 6, "2. DOCK BACKBOARD (120x80mm)", 2.5, ENGRAVE)
    sheet.rect(x0, y0, 120, 80, 2, 2, CUT)
    # 4x M3 Mounting Holes
    for dx, dy in [(6, 6), (114, 6), (6, 74), (114, 74)]:
        sheet.circle(x0 + dx, y0 + dy, 1.6, CUT)
    # ArUco Marker Placement Target (50mm x 50mm square engrave)
    sheet.rect(x0 + 35, y0 + 15, 50, 50, 0, 0, ENGRAVE)
    sheet.text(x0 + 38, y0 + 42, "ArUco #0 (50x50mm)", 2.2, ENGRAVE)
    # USB-C Female Port Infeed Cutout
    sheet.rect(x0 + 55, y0 + 68, 10.0, 4.2, 1.5, 1.5, CUT)
    sheet.circle(x0 + 50, y0 + 70, 1.1, CUT)
    sheet.circle(x0 + 70, y0 + 70, 1.1, CUT)

    # 3. Left & Right V-Shaped Guide Fences (130mm x 25mm each) at (140, 100) & (140, 135)
    for i, label in enumerate(["3A. LEFT V-FENCE", "3B. RIGHT V-FENCE"]):
        gx, gy = 140, 100 + i * 35
        sheet.text(gx + 2, gy + 5, f"{label} (Funnel Rail)", 2.0, ENGRAVE)
        sheet.rect(gx, gy, 130, 25, 2, 2, CUT)
        # Mounting holes to dock floor
        sheet.circle(gx + 15, gy + 12.5, 1.6, CUT)
        sheet.circle(gx + 65, gy + 12.5, 1.6, CUT)
        sheet.circle(gx + 115, gy + 12.5, 1.6, CUT)

    return sheet.to_svg()

if __name__ == "__main__":
    out_dir = os.path.join(os.path.dirname(__file__))
    chassis_svg = generate_chassis_sheet()
    chassis_path = os.path.join(out_dir, "walle_chassis_complete_cutsheet.svg")
    with open(chassis_path, "w", encoding="utf-8") as f:
        f.write(chassis_svg)
    print(f"Generated Chassis Cut-Sheet: {chassis_path}")

    dock_svg = generate_dock_sheet()
    dock_path = os.path.join(out_dir, "walle_charging_dock_cutsheet.svg")
    with open(dock_path, "w", encoding="utf-8") as f:
        f.write(dock_svg)
    print(f"Generated Dock Cut-Sheet: {dock_path}")
