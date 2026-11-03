# Project Alpha: Wall-E Autonomous Desktop Rover - Acrylic Chassis & Mechanical Cut-List

This guide provides the exact mechanical dimensions, cut-list, drill templates, and assembly instructions for constructing the Wall-E robot body using **2mm or 3mm acrylic sheets** and standard **M3 hardware standoffs**.

---

## 1. Overall Dimensions & Form Factor

* **Body Cube**: 100mm (Width) × 100mm (Depth) × 85mm (Height)
* **Total Height with Head Unit**: ~140mm – 150mm
* **Track Wheelbase / Footprint**: ~110mm (Width) × 120mm (Length)
* **Target Weight (with Battery & SBC)**: ~450g – 550g

---

## 2. Acrylic Plate Cut-List (Millimeter Specifications)

All plates are designed from standard flat 2mm or 3mm acrylic sheets.

```
       ┌────────────────────────────────────────────────────────┐
       │             BINOCULAR HEAD FACEPLATE                   │ 96mm x 46mm
       │ [Left Eye 33mm] ── [Center Camera 9mm] ── [Right 33mm] │
       └────────────────────────────────────────────────────────┘
  
       ┌────────────────────────┐
       │     TOP PLATE (LID)    │ 100mm x 100mm
       └────────────────────────┘
       ┌────────────────────────┐
       │   SEPARATOR DECK TRAY  │ 94mm x 94mm (Internal shelf)
       └────────────────────────┘
       ┌────────────────────────┐
       │    BOTTOM BASE PLATE   │ 100mm x 100mm
       └────────────────────────┘
  
  [FRONT: 100x85]   [BACK: 100x85]   [LEFT: 94x85]   [RIGHT: 94x85]
```

### Plate Detailed Specifications:

| Plate Name | Dimensions (W × H) | Qty | Key Cutouts & Mounting Holes |
| :--- | :---: | :---: | :--- |
| **A. Bottom Base Plate** | 100mm × 100mm | 1 | • 4x M3 corner standoff holes (5mm offset from edges).<br>• 4x mounting holes to bolt onto the crawler track chassis.<br>• 2x front edge slots for downward TCRT5000 cliff sensors. |
| **B. Separator Tray (Mid-Deck)** | 94mm × 94mm | 1 | • 4x M3 corner standoff pass-through holes.<br>• 4x M2.5 mounting holes for Raspberry Pi 4 (58mm × 49mm rectangle pattern).<br>• Central cable pass-through slot (15mm × 10mm). |
| **C. Top Plate (Access Lid)** | 100mm × 100mm | 1 | • 4x M3 corner standoff screw holes.<br>• Center rectangular cutout (24mm × 13mm) for MG90S Pan servo body.<br>• Slot for CSI camera ribbon cable & display wires. |
| **D. Front Chest Plate** | 100mm × 85mm | 1 | • Center cutout (20mm × 10mm) for VL53L0X ToF laser sensor window.<br>• 3mm hole for INMP441 microphone intake port.<br>• Decorative Wall-E solar charge level decal or power LED. |
| **E. Rear Access Plate** | 100mm × 85mm | 1 | • Rectangular cutout for KCD11 main power rocker switch.<br>• Cutout for USB-C charging port breakout board.<br>• SIM card slot access window. |
| **F. Left & Right Side Panels** | 94mm × 85mm | 2 | • Hex ventilation drill pattern for Raspberry Pi passive airflow.<br>• Mounting holes for side brackets / crawler track chassis. |
| **G. Binocular Head Faceplate** | 96mm × 46mm | 1 | • **Left Socket**: 33mm circular cutout for Left 1.28" Round LCD.<br>• **Center Bridge**: 9mm circular cutout for Pi Camera lens + 4x M2 mounting screw holes.<br>• **Right Socket**: 33mm circular cutout for Right 1.28" Round LCD.<br>• Perfect facial symmetry; zero parallax error for computer vision. |
| **H. Eye Brow Visors** | 45mm × 18mm | 2 | • Angled sun-shades glued/bolted above Left and Right eye sockets to give the authentic Wall-E curious expression. |

---

## 3. Standoff Internal Stacking Hierarchy

The robot uses standard **M3 hex standoffs** to form a rigid structural skeleton:

```
[TOP LID: 100x100mm] ── Pan/Tilt Head Mount
  │
  ├── 35mm Female-Female Standoffs (Upper Cavity: Pi 4, 4G Dongle, Audio Amp)
  │
[MID-DECK: 94x94mm] ──── Pi 4 Mounted Here
  │
  ├── 45mm Female-Female Standoffs (Lower Cavity: 2x 18650 Battery, Bucks, DRV8833)
  │
[BOTTOM BASE: 100x100mm] ── Bolted to Tank Crawler Tracks
```

---

## 4. Head Unit Assembly (Pan / Tilt Mechanism)

```
                       [Dual Binocular Eyes]
              (Left LCD) ── [Center Camera] ── (Right LCD)
                                ▲
                                │
                    [Tilt Servo MG90S] (Up / Down)
                                ▲
                                │
                    [Pan Servo MG90S]  (Left / Right)
                                ▲
                                │
                        [Top Acrylic Lid]
```

1. **Mounting Pan Servo**: The Pan servo is inserted into the top plate's center cutout from underneath, with its gear horn facing upward.
2. **Mounting Tilt Bracket**: The mini FPV gimbal bracket attaches to the Pan servo horn.
3. **Mounting Tilt Servo & Faceplate**: The Tilt servo sits sideways inside the bracket. The acrylic binocular faceplate screws onto the Tilt horn.
4. **Wiring Slack**: Ensure the CSI camera ribbon cable and 7 display jumper wires have **5cm–7cm of loose slack** so the head can freely pan 180° and tilt 60° without snagging or pulling wires out of the Raspberry Pi.

---

## 5. Acrylic Fabrication Guide (Hand Tools or Laser)

* **If Scoring by Hand**:
  1. Clamp a steel ruler firmly along the cut line with G-clamps.
  2. Use a plastic/acrylic scoring blade to score 4–6 times until a groove ~1/3 of the sheet thickness is formed.
  3. Place the scored line along the edge of a flat table, hold the sheet down firmly, and apply quick downward pressure on the overhang. It will snap with a clean edge.
* **If Drilling Holes**:
  * Acrylic is prone to catching and cracking with standard high-speed wood/metal bits.
  * **Tip**: Place blue painter's tape over both sides before drilling. Use low drill speed with gentle downward pressure. Back the acrylic with a scrap piece of wood.
  * For the 33mm eye display cutout: Use a 32mm–34mm bi-metal hole saw at very low RPM, or drill a ring of small 2mm holes and file smooth.
