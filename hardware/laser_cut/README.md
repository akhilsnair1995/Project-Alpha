# Project Alpha: Wall-E 100% Pre-Cut Laser Blueprints (Zero-Drill Guide)

This folder contains the complete, 1:1 scale laser cut sheets for Project Alpha. Every screw hole, display bezel, camera aperture, servo ear slot, and charging contact hole is pre-modeled. **No drilling is required.**

---

## 1. Blueprint Files

| File | Target Material & Thickness | Minimum Sheet Size | Description |
| :--- | :--- | :---: | :--- |
| [**`walle_chassis_complete_cutsheet.svg`**](file:///c:/Users/akhil/AI%20Playground/Project%20Alpha/hardware/laser_cut/walle_chassis_complete_cutsheet.svg) | 2mm or 3mm Cast Acrylic (Yellow, Smoked, or Clear) | 570mm × 280mm (Fits 600×300mm / 24"×12") | All 7 body plates + complete 6-plate enclosed 3D head box + dual visors (15 plates total). |
| [**`walle_charging_dock_cutsheet.svg`**](file:///c:/Users/akhil/AI%20Playground/Project%20Alpha/hardware/laser_cut/walle_charging_dock_cutsheet.svg) | 2mm or 3mm Cast Acrylic (Black or Clear) | 300mm × 200mm (A4) | Dock floor ramp, backboard with ArUco target, and V-shaped self-centering funnel rails. |
| [**`generate_blueprints.py`**](file:///c:/Users/akhil/AI%20Playground/Project%20Alpha/hardware/laser_cut/generate_blueprints.py) | Python script | — | Re-generates the SVGs with mathematical millimeter precision if dimensions need tweaking. |

---

## 2. Standard Laser Cutter Color Code

When submitting these files to a laser cutting service (e.g. Ponoko, Elecrow, local makerspace, or desktop cutter):

* **RED Lines (`#FF0000`, 0.1mm stroke)**: **Vector Through-Cut**. The laser cuts all the way through the acrylic.
* **BLUE Lines & Text (`#0000FF`)**: **Vector Score / Engrave**. Low power surface etching for part labels, ArUco target frame, and alignment guides.

---

## 3. Plate & Cutout Mapping (Verification Checklist)

Every hole in the blueprint is dimensioned for exact hardware drop-in:

### 1. Bottom Base Plate (100mm × 100mm)
* **4x Corner Standoff Holes**: 3.2mm diameter for M3 hex standoffs (90mm × 90mm spacing).
* **2x Charging Contactor Holes**: 3.2mm diameter spaced 30mm apart, 20mm from rear edge. Accepts M3 brass contact studs.
* **2x Front Cliff Sensor Slots**: 10mm × 6mm rectangular slots + M3 screw holes for TCRT5000 IR cliff sensors.
* **4x Track/Motor Slots**: 3.2mm × 12mm slots for bolting standard N20 motor brackets.

### 2. Separator Mid-Deck Tray (94mm × 94mm)
* **4x M3 Pass-Through Holes**: Aligns with the 90mm × 90mm corner standoffs.
* **4x M2.5 Raspberry Pi 4 Holes**: Exact 58.0mm × 49.0mm pattern for standard Pi mounting.
* **Central Cable Slot**: 24mm × 10mm rounded slot for routing power and motor wires between lower and upper decks.

### 3. Top Access Lid (100mm × 100mm)
* **Center Pan Servo Slot**: 23.5mm × 12.5mm rectangular cutout for the MG90S neck rotation servo body.
* **2x Servo Mounting Holes**: 2.2mm diameter spaced 28mm apart for the servo ear screws.
* **Dual Cable Pass-Through Slots**: 20mm × 6mm slots for the camera CSI ribbon and display SPI wires.
* **TTP223 Touch Sensor Mount**: Pre-cut M2 screw holes under the top lid.

### 4. 6-Plate Enclosed 3D Binocular Head Unit
* **Head Front (96mm × 46mm)**:
  * Left Eye: 33.5mm circular cutout for Left 1.28" Round LCD + 4x M2 mounting holes.
  * Right Eye: 33.5mm circular cutout for Right 1.28" Round LCD + 4x M2 mounting holes.
  * Center Bridge: 9.0mm circular aperture for Pi Camera lens + 4x M2 holes for Camera V2 PCB.
  * 4x M2.5 corner standoff holes to bolt to the rear plate.
* **Head Rear (96mm × 46mm)**:
  * 4x M2.5 corner standoff holes matching the front plate.
  * Central cable exit slot (26mm × 12mm) for camera CSI ribbon and display wires.
  * 2x M2.5 mounting holes for Tilt servo horn connection.
* **Head Top Cover (96mm × 25mm)**:
  * Roof of the head box. 4x corner holes + 2x mounting holes for Left and Right Eyebrow Visors.
* **Head Bottom Cover (96mm × 25mm)**:
  * Floor of the head box. Center tilt gimbal pivot mount & cable routing slot.
* **Head Left & Right Side Covers (25mm × 46mm each)**:
  * Encloses both sides, keeping dust and light out of the dual-screen housing.
* **Dual Eyebrow Visors (45mm × 18mm each)**:
  * Angled sun-shades bolted onto the top cover.

### 6. Front Chest Plate (100mm × 85mm)
* **VL53L0X Laser Distance Sensor**: 18mm × 8mm optical window + 2x M2 mounting holes.
* **INMP441 Microphone**: 3.2mm acoustic intake port + 2x M2 mounting holes.
* **Solar Gauge Slot**: 32mm × 7mm decorative viewing window for LED status.

### 7. Rear Access Plate (100mm × 85mm)
* **KCD11 Rocker Switch**: 19.5mm × 13.0mm snap-in cutout.
* **USB-C Charging Board**: 10.0mm × 4.2mm cutout + 2x M2 mounting holes.
* **SIM / MicroSD Inspection Slot**: 25mm × 12mm service access window.

### 8. Left & Right Side Panels (94mm × 85mm each)
* **Ventilation Grid**: 20x 3.0mm airflow holes strategically positioned directly across from the Raspberry Pi 4 CPU.

---

## 4. How to Order / Cut

1. **Ordering Online (e.g. Elecrow / Ponoko / Local fab lab)**:
   * Upload `walle_chassis_complete_cutsheet.svg` and `walle_charging_dock_cutsheet.svg`.
   * Select **3mm Cast Acrylic** (Yellow for authentic Wall-E, or Smoked Black for sleek modern look).
   * Specify: *"Red lines = cut, Blue lines = engrave/score, 1:1 scale millimeter"*.
2. **When the parts arrive**:
   * Peel the protective paper film.
   * Assemble using the M3 standoffs and M2/M2.5 screws—everything drops right into place with zero drilling!
