"""
SVG Blueprint Generator for Project Alpha: Wall-E Autonomous Rover & Charging Dock.
Generates 1:1 scale laser-ready SVGs with:
- Full 6-Plate Enclosed 3D Binocular Head Unit (Front, Back, Top, Bottom, Left, Right + Visors)
- Complete Chassis with Pre-Cut Holes, Slots, and Charging Contacts
- Autonomous Charging Dock with V-Funnel Guides and ArUco Target
- Zero Text Overlap & Standard Laser Cutter Color Coding (Red = Cut, Blue = Engrave)
"""

import os

class SVGSheet:
    def __init__(self, width_mm, height_mm, title="Laser Cut Sheet"):
        self.width = width_mm
        self.height = height_mm
        self.title = title
        self.elements = []

    def rect(self, x, y, w, h, rx=0, ry=0, color="#FF0000", stroke_width=0.1):
        self.elements.append(
            f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" '
            f'rx="{rx:.2f}" ry="{ry:.2f}" fill="none" stroke="{color}" stroke-width="{stroke_width:.2f}" />'
        )

    def circle(self, cx, cy, r, color="#FF0000", stroke_width=0.1):
        self.elements.append(
            f'<circle cx="{cx:.2f}" cy="{cy:.2f}" r="{r:.2f}" '
            f'fill="none" stroke="{color}" stroke-width="{stroke_width:.2f}" />'
        )

    def text(self, x, y, text, size=3.0, color="#0000FF", anchor="middle"):
        clean_text = (
            str(text)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        self.elements.append(
            f'<text x="{x:.2f}" y="{y:.2f}" font-family="Arial, sans-serif" '
            f'font-size="{size:.2f}" text-anchor="{anchor}" fill="{color}">{clean_text}</text>'
        )

    def to_svg(self):
        header = (
            f'<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n'
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{self.width}mm" height="{self.height}mm" '
            f'viewBox="0 0 {self.width} {self.height}">\n'
            f'<!-- {self.title} - 1:1 Scale Millimeter Precision -->\n'
            f'<!-- RED = Vector Cut (#FF0000), BLUE = Surface Engrave/Score (#0000FF) -->\n'
        )
        body = "\n".join(f"  {el}" for el in self.elements)
        footer = "\n</svg>\n"
        return header + body + footer


def generate_chassis_sheet():
    # 570mm x 280mm sheet (fits standard 600mm x 300mm / 24" x 12" acrylic sheet)
    sheet = SVGSheet(570, 280, "Project Alpha - Wall-E Complete Chassis & Enclosed Head Cut-Sheet")
    
    CUT = "#FF0000"
    ENGRAVE = "#0000FF"

    # Title Banner
    sheet.text(285, 8, "PROJECT ALPHA: WALL-E ROVER & 6-PLATE HEAD ENCLOSURE (3mm ACRYLIC)", 3.8, ENGRAVE, "middle")

    # =========================================================================
    # COLUMN 1: Base (Top) + Front Chest (Bottom)
    # =========================================================================
    col1_x = 15

    # 1. BOTTOM BASE PLATE (100mm x 100mm)
    y1 = 25
    sheet.text(col1_x + 50, y1 - 4, "1. BOTTOM BASE (100x100mm)", 2.6, ENGRAVE, "middle")
    sheet.rect(col1_x, y1, 100, 100, 2, 2, CUT)
    # 4x M3 Corner Standoff Holes (5mm offset from edges -> 90x90mm pattern)
    for dx, dy in [(5, 5), (95, 5), (5, 95), (95, 95)]:
        sheet.circle(col1_x + dx, y1 + dy, 1.6, CUT)
    # 2x Underside Charging Contactor Holes (30mm apart, 20mm from rear edge)
    sheet.circle(col1_x + 35, y1 + 80, 1.6, CUT)
    sheet.circle(col1_x + 65, y1 + 80, 1.6, CUT)
    sheet.text(col1_x + 35, y1 + 74, "(+)", 2.2, ENGRAVE, "middle")
    sheet.text(col1_x + 65, y1 + 74, "(-)", 2.2, ENGRAVE, "middle")
    # 2x Cliff Sensor Slots on Front (TCRT5000)
    sheet.rect(col1_x + 8, y1 + 4, 10, 6, 1, 1, CUT)
    sheet.circle(col1_x + 13, y1 + 14, 1.6, CUT)
    sheet.rect(col1_x + 82, y1 + 4, 10, 6, 1, 1, CUT)
    sheet.circle(col1_x + 87, y1 + 14, 1.6, CUT)
    # 4x Track Mounting Slots
    sheet.rect(col1_x + 20, y1 + 35, 12, 3.2, 1.6, 1.6, CUT)
    sheet.rect(col1_x + 20, y1 + 55, 12, 3.2, 1.6, 1.6, CUT)
    sheet.rect(col1_x + 68, y1 + 35, 12, 3.2, 1.6, 1.6, CUT)
    sheet.rect(col1_x + 68, y1 + 55, 12, 3.2, 1.6, 1.6, CUT)

    # 2. FRONT CHEST PLATE (100mm x 85mm)
    y2 = 155
    sheet.text(col1_x + 50, y2 - 4, "2. FRONT CHEST (100x85mm)", 2.6, ENGRAVE, "middle")
    sheet.rect(col1_x, y2, 100, 85, 2, 2, CUT)
    # 4x M3 Corner Standoff Holes
    for dx, dy in [(5, 5), (95, 5), (5, 80), (95, 80)]:
        sheet.circle(col1_x + dx, y2 + dy, 1.6, CUT)
    # VL53L0X ToF Laser Distance Sensor Window (18mm x 8mm)
    sheet.rect(col1_x + 41, y2 + 25, 18, 8, 1, 1, CUT)
    sheet.circle(col1_x + 36, y2 + 29, 1.1, CUT)
    sheet.circle(col1_x + 64, y2 + 29, 1.1, CUT)
    # INMP441 Microphone Acoustic Hole (3.2mm)
    sheet.circle(col1_x + 25, y2 + 50, 1.6, CUT)
    sheet.circle(col1_x + 20, y2 + 50, 1.1, CUT)
    sheet.circle(col1_x + 30, y2 + 50, 1.1, CUT)
    # Decorative Solar Gauge Cutout (32mm x 7mm)
    sheet.rect(col1_x + 48, y2 + 47, 32, 7, 1.5, 1.5, CUT)
    sheet.text(col1_x + 64, y2 + 60, "WALL-E", 2.2, ENGRAVE, "middle")

    # =========================================================================
    # COLUMN 2: Top Lid (Top) + Rear Access (Bottom)
    # =========================================================================
    col2_x = 135

    # 3. TOP ACCESS LID (100mm x 100mm)
    sheet.text(col2_x + 50, y1 - 4, "3. TOP LID (100x100mm)", 2.6, ENGRAVE, "middle")
    sheet.rect(col2_x, y1, 100, 100, 2, 2, CUT)
    for dx, dy in [(5, 5), (95, 5), (5, 95), (95, 95)]:
        sheet.circle(col2_x + dx, y1 + dy, 1.6, CUT)
    # Pan Servo Cutout (MG90S: 23.5mm x 12.5mm centered at x=50, y=50)
    sheet.rect(col2_x + 38.25, y1 + 43.75, 23.5, 12.5, 0.5, 0.5, CUT)
    sheet.circle(col2_x + 36, y1 + 50, 1.1, CUT)
    sheet.circle(col2_x + 64, y1 + 50, 1.1, CUT)
    # Dual Cable Pass-Through Slots
    sheet.rect(col2_x + 20, y1 + 75, 22, 6, 2, 2, CUT)
    sheet.rect(col2_x + 58, y1 + 75, 22, 6, 2, 2, CUT)
    # TTP223 Touch Sensor Mounting Holes
    sheet.circle(col2_x + 82, y1 + 25, 1.1, CUT)
    sheet.circle(col2_x + 92, y1 + 25, 1.1, CUT)

    # 4. REAR ACCESS PLATE (100mm x 85mm)
    sheet.text(col2_x + 50, y2 - 4, "4. REAR ACCESS (100x85mm)", 2.6, ENGRAVE, "middle")
    sheet.rect(col2_x, y2, 100, 85, 2, 2, CUT)
    for dx, dy in [(5, 5), (95, 5), (5, 80), (95, 80)]:
        sheet.circle(col2_x + dx, y2 + dy, 1.6, CUT)
    # KCD11 Power Switch Cutout (19.5mm x 13.0mm)
    sheet.rect(col2_x + 18, y2 + 25, 19.5, 13.0, 0.5, 0.5, CUT)
    sheet.text(col2_x + 28, y2 + 43, "POWER", 2.0, ENGRAVE, "middle")
    # USB-C Charging Port Cutout (10mm x 4.2mm)
    sheet.rect(col2_x + 60, y2 + 30, 10.0, 4.2, 1.5, 1.5, CUT)
    sheet.circle(col2_x + 54, y2 + 32, 1.1, CUT)
    sheet.circle(col2_x + 76, y2 + 32, 1.1, CUT)
    sheet.text(col2_x + 65, y2 + 42, "USB-C", 2.0, ENGRAVE, "middle")
    # SIM Card / MicroSD Service Inspection Slot
    sheet.rect(col2_x + 37, y2 + 54, 26.0, 12.0, 2.0, 2.0, CUT)
    sheet.text(col2_x + 50, y2 + 72, "SIM / SD", 2.0, ENGRAVE, "middle")

    # =========================================================================
    # COLUMN 3: Mid-Deck Tray (Top) + Left Side Vent (Bottom)
    # =========================================================================
    col3_x = 255

    # 5. SEPARATOR MID-DECK TRAY (94mm x 94mm)
    sheet.text(col3_x + 47, y1 - 4, "5. MID-DECK TRAY (94x94mm)", 2.6, ENGRAVE, "middle")
    sheet.rect(col3_x, y1, 94, 94, 2, 2, CUT)
    for dx, dy in [(2, 2), (92, 2), (2, 92), (92, 92)]:
        sheet.circle(col3_x + dx, y1 + dy, 1.6, CUT)
    # 4x M2.5 Raspberry Pi 4 Holes (58mm x 49mm centered at x=47, y=47)
    pi_cx, pi_cy = col3_x + 47, y1 + 47
    for dx in [-29, 29]:
        for dy in [-24.5, 24.5]:
            sheet.circle(pi_cx + dx, pi_cy + dy, 1.35, CUT)
    sheet.rect(pi_cx - 12, pi_cy + 8, 24, 10, 3, 3, CUT)

    # 6. LEFT SIDE VENT PANEL (94mm x 85mm)
    sheet.text(col3_x + 47, y2 - 4, "6. LEFT SIDE (94x85mm)", 2.6, ENGRAVE, "middle")
    sheet.rect(col3_x, y2, 94, 85, 2, 2, CUT)
    for dx, dy in [(2, 5), (92, 5), (2, 80), (92, 80)]:
        sheet.circle(col3_x + dx, y2 + dy, 1.6, CUT)
    for col in range(5):
        for row in range(4):
            sheet.circle(col3_x + 35 + col * 6, y2 + 35 + row * 6, 1.5, CUT)

    # =========================================================================
    # COLUMN 4: Right Side Vent (Top) + Head Front & Rear Plates
    # =========================================================================
    col4_x = 368

    # 7. RIGHT SIDE VENT PANEL (94mm x 85mm)
    sheet.text(col4_x + 47, y1 - 4, "7. RIGHT SIDE (94x85mm)", 2.6, ENGRAVE, "middle")
    sheet.rect(col4_x, y1, 94, 85, 2, 2, CUT)
    for dx, dy in [(2, 5), (92, 5), (2, 80), (92, 80)]:
        sheet.circle(col4_x + dx, y1 + dy, 1.6, CUT)
    for col in range(5):
        for row in range(4):
            sheet.circle(col4_x + 35 + col * 6, y1 + 35 + row * 6, 1.5, CUT)

    # 8. HEAD FRONT FACEPLATE (96mm x 46mm)
    y_hfront = 125
    sheet.text(col4_x + 48, y_hfront - 4, "8. HEAD FRONT (96x46mm)", 2.6, ENGRAVE, "middle")
    sheet.rect(col4_x, y_hfront, 96, 46, 3, 3, CUT)
    # 4x M2.5 Corner Standoff Holes (spacing 88mm x 38mm)
    for dx, dy in [(4, 4), (92, 4), (4, 42), (92, 42)]:
        sheet.circle(col4_x + dx, y_hfront + dy, 1.35, CUT)
    # Left Eye Cutout (33.5mm diameter) + 4x M2 screw holes
    lex, ley = col4_x + 23, y_hfront + 23
    sheet.circle(lex, ley, 16.75, CUT)
    for dx in [-18, 18]:
        for dy in [-18, 18]:
            sheet.circle(lex + dx, ley + dy, 1.1, CUT)
    # Right Eye Cutout (33.5mm diameter) + 4x M2 screw holes
    rex, rey = col4_x + 73, y_hfront + 23
    sheet.circle(rex, rey, 16.75, CUT)
    for dx in [-18, 18]:
        for dy in [-18, 18]:
            sheet.circle(rex + dx, rey + dy, 1.1, CUT)
    # Center Bridge Camera Lens Cutout (9.0mm diameter) + 4x M2 camera PCB holes
    cam_x, cam_y = col4_x + 48, y_hfront + 23
    sheet.circle(cam_x, cam_y, 4.5, CUT)
    for dx in [-10.5, 10.5]:
        for dy in [-6.25, 6.25]:
            sheet.circle(cam_x + dx, cam_y + dy, 1.1, CUT)

    # 9. HEAD REAR ENCLOSURE PLATE (96mm x 46mm)
    y_hrear = 195
    sheet.text(col4_x + 48, y_hrear - 4, "9. HEAD REAR (96x46mm)", 2.6, ENGRAVE, "middle")
    sheet.rect(col4_x, y_hrear, 96, 46, 3, 3, CUT)
    # 4x M2.5 Corner Standoff Holes (matches Front Plate exactly!)
    for dx, dy in [(4, 4), (92, 4), (4, 42), (92, 42)]:
        sheet.circle(col4_x + dx, y_hrear + dy, 1.35, CUT)
    # Central Cable Exit Slot (26mm x 12mm)
    sheet.rect(col4_x + 35, y_hrear + 17, 26, 12, 2, 2, CUT)
    # 2x Tilt Bracket Horn Connection Holes
    sheet.circle(col4_x + 40, y_hrear + 37, 1.35, CUT)
    sheet.circle(col4_x + 56, y_hrear + 37, 1.35, CUT)

    # =========================================================================
    # COLUMN 5: Head 4 Side Covers + Dual Visors (Encloses the 3D Head Box)
    # =========================================================================
    col5_x = 480

    # 10. HEAD TOP COVER (96mm x 25mm)
    y_htop = 25
    sheet.text(col5_x + 48, y_htop - 4, "10. HEAD TOP (96x25mm)", 2.4, ENGRAVE, "middle")
    sheet.rect(col5_x, y_htop, 96, 25, 2, 2, CUT)
    # 4x M2.5 Corner Screw Holes
    for dx, dy in [(4, 4), (92, 4), (4, 21), (92, 21)]:
        sheet.circle(col5_x + dx, y_htop + dy, 1.35, CUT)
    # Visor Mount Holes (Left & Right Visor screws)
    sheet.circle(col5_x + 23, y_htop + 12.5, 1.1, CUT)
    sheet.circle(col5_x + 73, y_htop + 12.5, 1.1, CUT)

    # 11. HEAD BOTTOM COVER (96mm x 25mm)
    y_hbot = 68
    sheet.text(col5_x + 48, y_hbot - 4, "11. HEAD BOTTOM (96x25mm)", 2.4, ENGRAVE, "middle")
    sheet.rect(col5_x, y_hbot, 96, 25, 2, 2, CUT)
    for dx, dy in [(4, 4), (92, 4), (4, 21), (92, 21)]:
        sheet.circle(col5_x + dx, y_hbot + dy, 1.35, CUT)
    # Cable Pass-Through Slot & Tilt Pivot Mount
    sheet.rect(col5_x + 35, y_hbot + 7.5, 26, 10, 2, 2, CUT)

    # 12 & 13. HEAD LEFT & RIGHT SIDE COVERS (25mm x 46mm each)
    y_hsides = 115
    sheet.text(col5_x + 48, y_hsides - 4, "12 & 13. HEAD SIDES (25x46mm)", 2.3, ENGRAVE, "middle")
    # Left Side Cover
    sheet.rect(col5_x + 10, y_hsides, 25, 46, 2, 2, CUT)
    sheet.circle(col5_x + 22.5, y_hsides + 5, 1.35, CUT)
    sheet.circle(col5_x + 22.5, y_hsides + 41, 1.35, CUT)
    # Right Side Cover
    sheet.rect(col5_x + 55, y_hsides, 25, 46, 2, 2, CUT)
    sheet.circle(col5_x + 67.5, y_hsides + 5, 1.35, CUT)
    sheet.circle(col5_x + 67.5, y_hsides + 41, 1.35, CUT)

    # 14 & 15. DUAL EYEBROW VISORS (45mm x 18mm each)
    y_vis = 185
    sheet.text(col5_x + 48, y_vis - 4, "14 & 15. DUAL VISORS (45x18mm)", 2.4, ENGRAVE, "middle")
    sheet.rect(col5_x, y_vis, 45, 18, 2, 2, CUT)
    sheet.circle(col5_x + 10, y_vis + 13, 1.1, CUT)
    sheet.circle(col5_x + 35, y_vis + 13, 1.1, CUT)

    sheet.rect(col5_x + 51, y_vis, 45, 18, 2, 2, CUT)
    sheet.circle(col5_x + 61, y_vis + 13, 1.1, CUT)
    sheet.circle(col5_x + 86, y_vis + 13, 1.1, CUT)

    return sheet.to_svg()


def generate_dock_sheet():
    # Sheet for Charging Dock (300mm x 220mm)
    sheet = SVGSheet(300, 220, "Project Alpha - Wall-E Charging Dock Cut-Sheet")
    CUT = "#FF0000"
    ENGRAVE = "#0000FF"

    # Title
    sheet.text(150, 8, "PROJECT ALPHA: CHARGING DOCK (3mm ACRYLIC)", 3.8, ENGRAVE, "middle")

    # 1. Dock Floor Plate (120mm x 140mm)
    x1, y1 = 15, 25
    sheet.text(x1 + 60, y1 - 4, "1. DOCK FLOOR RAMP (120x140mm)", 2.8, ENGRAVE, "middle")
    sheet.rect(x1, y1, 120, 140, 2, 2, CUT)
    for dx, dy in [(6, 6), (114, 6), (6, 134), (114, 134)]:
        sheet.circle(x1 + dx, y1 + dy, 1.6, CUT)
    # Left (+) rail: 15mm x 50mm
    sheet.rect(x1 + 40, y1 + 55, 15, 50, 2, 2, CUT)
    sheet.circle(x1 + 47.5, y1 + 48, 1.6, CUT)
    sheet.text(x1 + 47.5, y1 + 42, "(+)", 2.5, ENGRAVE, "middle")
    # Right (-) rail: 15mm x 50mm
    sheet.rect(x1 + 65, y1 + 55, 15, 50, 2, 2, CUT)
    sheet.circle(x1 + 72.5, y1 + 48, 1.6, CUT)
    sheet.text(x1 + 72.5, y1 + 42, "(-)", 2.5, ENGRAVE, "middle")
    sheet.text(x1 + 60, y1 + 125, "ROBOT ENTRANCE", 2.2, ENGRAVE, "middle")

    # 2. Dock Backboard (120mm x 80mm)
    x2, y2 = 155, 25
    sheet.text(x2 + 60, y2 - 4, "2. DOCK BACKBOARD (120x80mm)", 2.8, ENGRAVE, "middle")
    sheet.rect(x2, y2, 120, 80, 2, 2, CUT)
    for dx, dy in [(6, 6), (114, 6), (6, 74), (114, 74)]:
        sheet.circle(x2 + dx, y2 + dy, 1.6, CUT)
    # ArUco Marker Placement Target Frame (50mm x 50mm)
    sheet.rect(x2 + 35, y2 + 10, 50, 50, 0, 0, ENGRAVE)
    sheet.text(x2 + 60, y2 + 36, "ArUco #0", 2.5, ENGRAVE, "middle")
    sheet.text(x2 + 60, y2 + 42, "(50x50mm)", 2.0, ENGRAVE, "middle")
    # USB-C Female Port Infeed Cutout
    sheet.rect(x2 + 55, y2 + 66, 10.0, 4.2, 1.5, 1.5, CUT)
    sheet.circle(x2 + 50, y2 + 68, 1.1, CUT)
    sheet.circle(x2 + 70, y2 + 68, 1.1, CUT)

    # 3. Left & Right V-Shaped Guide Fences (125mm x 25mm each)
    y3 = 130
    sheet.text(155 + 60, y3 - 4, "3. V-SHAPED GUIDE FENCES (125x25mm)", 2.4, ENGRAVE, "middle")
    for i, label in enumerate(["3A. LEFT FUNNEL", "3B. RIGHT FUNNEL"]):
        gy = y3 + i * 32
        sheet.rect(155, gy, 125, 25, 2, 2, CUT)
        sheet.circle(155 + 15, gy + 12.5, 1.6, CUT)
        sheet.circle(155 + 62.5, gy + 12.5, 1.6, CUT)
        sheet.circle(155 + 110, gy + 12.5, 1.6, CUT)
        sheet.text(155 + 62.5, gy + 8, label, 1.8, ENGRAVE, "middle")

    return sheet.to_svg()


if __name__ == "__main__":
    import xml.etree.ElementTree as ET

    out_dir = os.path.dirname(__file__)
    
    # 1. Generate & Validate Chassis Cut-Sheet
    chassis_svg = generate_chassis_sheet()
    try:
        ET.fromstring(chassis_svg)
        print("[OK] Chassis SVG is 100% valid XML.")
    except ET.ParseError as e:
        print(f"[ERROR] Chassis SVG XML Syntax Error: {e}")
        raise

    chassis_path = os.path.join(out_dir, "walle_chassis_complete_cutsheet.svg")
    with open(chassis_path, "w", encoding="utf-8") as f:
        f.write(chassis_svg)
    print(f"Generated Chassis Cut-Sheet: {chassis_path}")

    # 2. Generate & Validate Dock Cut-Sheet
    dock_svg = generate_dock_sheet()
    try:
        ET.fromstring(dock_svg)
        print("[OK] Dock SVG is 100% valid XML.")
    except ET.ParseError as e:
        print(f"[ERROR] Dock SVG XML Syntax Error: {e}")
        raise

    dock_path = os.path.join(out_dir, "walle_charging_dock_cutsheet.svg")
    with open(dock_path, "w", encoding="utf-8") as f:
        f.write(dock_svg)
    print(f"Generated Dock Cut-Sheet: {dock_path}")
