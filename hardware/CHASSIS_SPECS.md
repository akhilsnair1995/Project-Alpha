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
| **A. Bottom Base Plate** | 100mm × 100mm | 1 | • 4x M3 corner standoff & internal L-bracket holes (84mm × 84mm pattern, 8mm edge offset).<br>• 4x mounting slots to bolt onto N20 motor brackets & track chassis.<br>• 2x front edge slots for downward TCRT5000 cliff sensors (8.4mm margin to corner holes).<br>• 2x underside charging contactor stud holes. |
| **B. Separator Tray (Mid-Deck)** | 94mm × 94mm | 1 | • 4x M3 corner standoff pass-through holes (84mm × 84mm pattern, **3.4mm safe acrylic margin**).<br>• 4x M2.5 mounting holes for Raspberry Pi 4/5 (58mm × 49mm rectangle pattern).<br>• Central cable pass-through slot (24mm × 10mm). |
| **C. Top Plate (Access Lid)** | 100mm × 100mm | 1 | • 4x M3 corner standoff & internal L-bracket screw holes.<br>• Center rectangular cutout (23.0mm × 12.5mm) + 2x 2.2mm holes (28mm pitch) for MG90S Pan servo body.<br>• Dual slots for CSI camera ribbon cable & display wires.<br>• Pre-cut M2 mounting holes for TTP223 touch sensor. |
| **D. Front Chest Plate** | 100mm × 85mm | 1 | • 4x M3 corner holes for internal L-brackets (8mm offset).<br>• Center cutout (18mm × 8mm) + 2x M2 mounting holes for VL53L0X ToF laser sensor.<br>• 3.2mm acoustic intake hole + 2x M2 holes for INMP441 microphone.<br>• Decorative Wall-E solar charge gauge window. |
| **E. Rear Access Plate** | 100mm × 85mm | 1 | • 4x M3 corner holes for internal L-brackets.<br>• Snap-in cutout (19.5mm × 13.0mm) for KCD11 main power rocker switch.<br>• Cutout (10mm × 4.2mm) + 2x M2 holes for USB-C charging port breakout board.<br>• SIM / MicroSD inspection slot (26mm × 12mm). |
| **F1. Left Side Panel (Active Fan)** | 94mm × 85mm | 1 | • **40mm Active Cooling Fan Mount**: 36mm circular intake aperture + 4x M3 screw holes (32mm × 32mm square pattern).<br>• Bolts any standard 4010 5V fan directly to the acrylic with zero drilling.<br>• 4x M3 corner holes for internal L-brackets (4.4mm edge margin). |
| **F2. Right Side Panel (Exhaust)** | 94mm × 85mm | 1 | • Air exhaust ventilation grid (20x 3mm airflow holes).<br>• Creates a continuous forced-air cooling wind tunnel across the Pi 5 Active Cooler.<br>• 4x M3 corner holes for internal L-brackets (4.4mm edge margin). |
| **G. Head Front Faceplate** | 96mm × 46mm | 1 | • **Left Eye Socket**: 33.5mm circular socket for Left 1.28" Round LCD (bezel press-fit).<br>• **Center Bridge**: 9.0mm circular aperture for Pi Camera lens.<br>• **Camera PCB Mount**: 4x M2 holes in portrait orientation (12.5mm × 21.0mm pattern, **2.77mm clean solid clearance** to both eye apertures, zero overlap).<br>• **Right Eye Socket**: 33.5mm circular socket for Right 1.28" Round LCD (bezel press-fit).<br>• 4x M2.5 corner standoff holes (86mm × 36mm pattern, 8.07mm clearance to eye cutouts). |
| **H. Head Rear Plate** | 96mm × 46mm | 1 | • 4x M2.5 corner standoff holes matching front plate.<br>• Central cable exit slot (26mm × 12mm) for camera CSI ribbon and display wires.<br>• 2x M2.5 mounting holes for Tilt servo horn connection. |
| **I. Head Top Cover** | 96mm × 25mm | 1 | • Roof of head enclosure.<br>• 4x corner holes to fasten to front/rear frame.<br>• 2x screw holes for Left & Right eyebrow visors. |
| **J. Head Bottom Cover** | 96mm × 25mm | 1 | • Floor of head enclosure.<br>• Center cable pass-through slot and tilt gimbal pivot mount. |
| **K & L. Head Side Covers** | 25mm × 46mm | 2 | • Left and Right walls enclosing the head box.<br>• Fastens to corner standoffs. |
| **M. Eye Brow Visors** | 45mm × 18mm | 2 | • Angled sun-shades bolted above Left and Right eye sockets to give the authentic Wall-E curious expression. |

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

## 4. Head Unit 3D Box Assembly (Enclosed Housing)

The head is a fully enclosed 3D box (96mm W × 46mm H × 25mm D) that protects the dual screens and camera from dust and physical impact:

```
                      [TOP COVER (96x25mm)] ── Mounts Visors
                               │
[LEFT (25x46)] ── [FRONT (96x46)] ─── 4x 25mm Standoffs ─── [REAR (96x46)] ── [RIGHT (25x46)]
                               │
                    [BOTTOM COVER (96x25mm)] ── Tilt Horn Mount
                               │
                       [Tilt Servo MG90S] (Up / Down)
                               ▲
                               │
                       [Pan Servo MG90S]  (Left / Right)
                               ▲
                               │
                       [Top Acrylic Lid]
```

1. **Internal Frame**: 4x M2.5 × 25mm female-female standoffs connect the **Front Faceplate** and **Rear Plate** at their 4 corners, creating a rigid protective cage around the two 1.28" LCD modules and the center Pi Camera board.
2. **Side Enclosures**: The **Top Cover**, **Bottom Cover**, **Left Cover**, and **Right Cover** screw onto this frame, creating a complete, clean 6-sided 3D housing with zero exposed electronics.
3. **Visors**: The dual eyebrow visors bolt directly to the pre-cut holes on the Top Cover at an angle.
4. **Mounting to Neck**: The Tilt servo horn screws directly into the Bottom Cover and Rear Plate's pre-cut mounting holes.
5. **Wiring Slack**: Cables exit smoothly through the central rear/bottom slots down into the main body, with 5cm–7cm of loose slack for 180° pan and 60° tilt motion.

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
