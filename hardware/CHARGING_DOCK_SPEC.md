# Project Alpha: Wall-E Autonomous Charging Dock & Contactor System

This specification details the autonomous docking station, underside electrical contactor pins, reverse-polarity protection, and visual homing guidance that allows Wall-E to find its charger and dock automatically when low on battery.

---

## 1. Underside Contactor Pin Design (Robot Side)

Because the robot will be built without drills, the bottom plate has **pre-cut 3.2mm contactor holes** located toward the rear centerline.

```
       [Wall-E Underside View - Base Plate]
     ┌──────────────────────────────────────┐
     │ [Cliff L]                  [Cliff R] │  <-- Front (Drives onto dock first)
     │                                      │
     │      (Track L)        (Track R)      │
     │                                      │
     │            (30mm Spacing)            │
     │              (+)      (-)            │  <-- Pre-cut 3.2mm Contactor Holes
     │             [ ○ ]    [ ○ ]           │      (M3 Brass Contact Studs)
     └──────────────────────────────────────┘  <-- Rear
```

### Physical Contactor Hardware:
* **Option A: M3 Brass Pan-Head Screws (Simplest, Most Rugged)**:
  * Two M3 × 12mm brass screws inserted from the bottom with the smooth, curved pan-head facing downward.
  * Secured from the inside with an M3 brass nut + tooth lock washer + ring crimp terminal.
  * The brass heads protrude **2mm–3mm** beneath the bottom acrylic plate, acting as low-resistance contact skid-shoes.
* **Option B: Heavy-Duty Spring-Loaded Pogo Pins**:
  * 2x 5A–10A brass barrel pogo pins fitted through the 3.2mm holes. Spring compression ensures solid continuous contact even on slightly uneven surfaces.

---

## 2. Reverse Polarity & Short-Circuit Safety Circuit

> [!IMPORTANT]
> If Wall-E drives across a metallic surface or conductive object on the floor, the exposed contact pins must **never** short the internal 18650 battery cells or cause sparks.

```
[Under-Chassis Contacts]
      (+) Contact Pad ──────[ SS54 Schottky Diode ]───► [+] 5V-9V Input to
                               (Blocks back-feed)            IP2326 2S Charger Board
                                                                   │
                                                                   ▼
                                                            2S Li-ion Battery
                                                               (Isolated)
      (-) Contact Pad ────────────────────────────────► [-] GND Input to Charger
```

* **SS54 Schottky Diode (or Ideal Diode Controller)**:
  * Rated for 5A continuous, with only ~0.35V forward drop.
  * Ensures electrical current can **only flow INTO the robot** from the dock.
  * Current can **never flow out** from the robot's battery to the exposed contact studs. Touching a coin, key, or wire between the contacts will produce zero voltage and zero risk.
* **Charging Detection Signal**:
  * A tap from the diode cathode is connected to Raspberry Pi `GPIO 26` (via a 10k/10k voltage divider).
  * When Wall-E successfully contacts the dock, this pin transitions **HIGH**, instantly signaling the software: *"Charging contacts engaged!"*

---

## 3. Autonomous Homing & Visual Docking Strategy

Wall-E uses its **center-bridge camera** and **ArUco / AprilTag fiducial tracking** in OpenCV to dock autonomously.

```
             ┌───────────────────────────────┐
             │     CHARGING DOCK BACKBOARD   │
             │                               │
             │        ┌─────────────┐        │
             │        │  ArUco #0   │        │  <-- High-contrast optical marker
             │        │  (50x50mm)  │        │      (Recognised from 2m away)
             │        └─────────────┘        │
             │                               │
             ├───────────────────────────────┤
             │  \                         /  │
             │   \  V-SHAPED GUIDE RAILS /   │  <-- Acrylic funnel aligns tracks
             │    │                     │    │
             │    │  [+]             [-]│    │  <-- Sprung Copper / Brass Contact
             │    │  RAIL            RAIL│   │      Plates on Dock Floor
             └────┴─────────────────────┴────┘
```

### The Autonomous Docking Algorithm:

1. **Low Battery Trigger**:
   * Battery voltage reaches **< 6.8V** (approx 15% remaining capacity).
   * Wall-E stops current activities, droops its head slightly, and plays a low-energy chirp.
2. **Search & Locate**:
   * Pan/tilt servos scan the room until the camera detects **ArUco Marker #0** on the dock.
   * OpenCV calculates the 3D position vector: distance $Z$, lateral offset $X$, and yaw angle $\theta$.
3. **Approach & Alignment**:
   * Uses a proportional-integral (PI) heading controller: adjusts left/right crawler track speeds to keep $X \approx 0$ and angle $\theta \approx 0$.
   * As it gets within 20cm, it slows down to minimum crawl speed.
4. **Dock Ingress (Mechanical Self-Centering)**:
   * The dock features **V-shaped acrylic guide fences** that funnel Wall-E's tracks straight into position even if approaching at an angle.
5. **Contact Confirmation & Sleep Mode**:
   * As the brass contact pins slide onto the dock's spring-loaded copper plates, the `GPIO 26` pin detects charging voltage.
   * Wall-E immediately cuts motor power, centers its neck, plays the **iconic Wall-E solar charge chime**, and displays animated sleeping "Zzz" eyes on the dual screens while battery charges.

---

## 4. Charging Dock Mechanical Design

The dock itself is built from matching laser-cut acrylic pieces:
* **Floor Ramp**: 120mm (W) × 140mm (L) with a shallow 10-degree entry lip so Wall-E rolls smoothly onto it.
* **Funnel Rails**: Two 45-degree guide walls on the left and right that guide the tracks into a precise 112mm channel.
* **Contact Strips**: Two 20mm × 60mm self-adhesive copper foil strips (or sprung bronze battery leaf springs) connected to a standard USB-C female port on the rear of the dock.
* **Backstop Wall**: 120mm (W) × 80mm (H) holding the printed ArUco marker.
