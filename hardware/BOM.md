# Project Alpha: Wall-E Autonomous Desktop Rover - Bill of Materials (BOM)

This document contains the complete hardware component list, technical specifications, and procurement guidance for the physical Wall-E inspired autonomous rover.

---

## 1. Core Compute & Connectivity

| Item | Component | Specification / Model | Qty | Key Notes |
| :--- | :--- | :--- | :---: | :--- |
| **1.1** | **Main Computer (SBC)** | **Raspberry Pi 4 Model B** (2GB or 4GB) *(Alt: Raspberry Pi Zero 2 W)* | 1 | Runs Linux OS, local OpenCV face tracking, audio pipelines, and Gemini 2.5 API. Pi 4 is recommended for full USB ports and thermal stability under vision workloads. |
| **1.2** | **Cellular 4G LTE Modem** | **Waveshare 4G Dongle** *(or Huawei E3372 / SIM7600 USB)* | 1 | Plugs directly into Pi USB. Recognised natively in Linux as `eth1`/`wwan0`. Automatic cellular fallback when away from WiFi. |
| **1.3** | **IoT SIM Card** | Standard Nano SIM (Prepaid or IoT SIM like Hologram/Things Mobile/Local carrier) | 1 | Data-only SIM card with ~500MB–1GB/month for Gemini API and telemetry. |
| **1.4** | **Storage** | 32GB or 64GB MicroSD Card (Class 10 / A1 or A2) | 1 | High endurance (SanDisk Ultra / Extreme recommended). |

---

## 2. Vision & Facial Display (Wall-E Head)

| Item | Component | Specification / Model | Qty | Key Notes |
| :--- | :--- | :--- | :---: | :--- |
| **2.1** | **Eye Displays (Dual)** | **1.28-inch Round IPS LCD** (GC9A01 Driver) | **2** | 240x240 resolution, SPI interface. Dedicated Left and Right screens allowing coordinated pupil movement, independent blinking, winking, and squinting. Mounted symmetrically in the head. |
| **2.2** | **Nose-Bridge Camera** | **Raspberry Pi Camera Module V2** *(or 160° Wide-Angle OV5647)* | 1 | 5MP / 8MP, CSI ribbon cable interface (20cm–30cm flexible cable). **Centered between the two eyes** on the bridge. Eliminates parallax error for face tracking and gives Wall-E a symmetrical, authentic look. |
| **2.3** | **Pan/Tilt Servos** | **TowerPro MG90S** (Metal Gear 9g Micro-Servos) | 2 | **Must use metal gears.** Plastic gear (SG90) micro-servos will strip under the weight of the dual-screen head assembly. |
| **2.4** | **Pan/Tilt Bracket** | Mini 2-Axis FPV Servo Gimbal Bracket | 1 | Standard molded nylon or acrylic kit designed for 9g servos. Screws directly to top plate. |

---

## 3. Audio & Interaction

| Item | Component | Specification / Model | Qty | Key Notes |
| :--- | :--- | :--- | :---: | :--- |
| **3.1** | **Microphone** | **INMP441 I2S Omnidirectional Digital Mic** | 1 | Ultra-clean digital audio over I2S (no analog static or electrical buzz from motors). Mounted on chest plate. |
| **3.2** | **Audio Amplifier** | **MAX98357A I2S 3W Mono Class-D Amp** | 1 | Communicates over I2S to the Pi; directly drives the mini speaker with crisp speech. |
| **3.3** | **Speaker** | 8Ω (Ohm) 2W Miniature Speaker (28mm–30mm diameter) | 1 | Fits inside the acrylic body cavity. |
| **3.4** | **Touch Sensor** | **TTP223 Capacitive Touch Switch Module** | 1 | Mounted beneath the top shell or head visor. Triggers "petting" reactions when touched. |

---

## 4. Locomotion & Safety Sensors

| Item | Component | Specification / Model | Qty | Key Notes |
| :--- | :--- | :--- | :---: | :--- |
| **4.1** | **Track Chassis** | Mini Tracked Tank Rover Chassis Kit | 1 | Includes rubber tank treads, drive sprockets, idler wheels, and mounting plate. |
| **4.2** | **Drive Motors** | 2x N20 Micro Metal Gearmotors (6V, ~100–150 RPM) | 2 | Typically included with track kits. High torque, slow and deliberate crawler movement. |
| **4.3** | **Motor Driver** | **DRV8833** *(or TB6612FNG) Dual H-Bridge* | 1 | High efficiency MOSFET driver. Does NOT suffer the 1.5V–2V voltage drop of obsolete L298N drivers. |
| **4.4** | **Cliff Sensors** | **TCRT5000 IR Reflective Optical Sensor Modules** | 2 | Point downward at table surface on the front left and front right. Prevents rover from driving off desk edges. |
| **4.5** | **Obstacle Ranging** | **VL53L0X Time-of-Flight (ToF) Laser Distance Sensor** | 1 | I2C sensor. Gives millimeter-accurate distance readings up to 2m for obstacle avoidance. |

---

## 5. Power & Battery Management

| Item | Component | Specification / Model | Qty | Key Notes |
| :--- | :--- | :--- | :---: | :--- |
| **5.1** | **Battery Cells** | 2x 18650 3.7V Li-ion Rechargeable Cells (e.g. 2500–3500mAh) | 2 | Connected in series for a 7.4V nominal (8.4V peak) pack. |
| **5.2** | **Battery Holder** | 2S 18650 Battery Holder with Wire Leads | 1 | Holds both cells securely in the lower deck. |
| **5.3** | **2S Charger & BMS** | 2S 8.4V Type-C Li-ion Booster Charging Board (e.g. IP2326 or TP5100 based) | 1 | Allows recharging the robot using standard USB-C smartphone chargers. |
| **5.4** | **Logic Buck Converter** | **XL4015** *(or MP1584)* DC-DC Buck Module (Output set to 5.1V @ 3A–5A) | 1 | Dedicated to Raspberry Pi, 4G dongle, screen, and sensors. |
| **5.5** | **Motor Buck Converter** | **MP1584** DC-DC Step-Down Module (Output set to 5.5V–6.0V @ 2A) | 1 | **Isolated power rail** for the 2x MG90S servos and N20 drive motors to prevent CPU brownouts. |
| **5.6** | **Power Switch** | Mini Rocker Switch (KCD11) or SPST Toggle Switch | 1 | Cuts main 7.4V line from battery. |
| **5.7** | **ADC (Battery Level)** | **ADS1115** 16-Bit I2C ADC Module *(or 100k/47k voltage divider)* | 1 | Monitors battery discharge state and alerts when recharging is needed. |

---

## 6. Chassis & Mechanical Hardware (Acrylic Build)

| Item | Material | Specification | Qty | Key Notes |
| :--- | :--- | :--- | :---: | :--- |
| **6.1** | **Acrylic Sheets** | 2mm or 3mm thickness, A4 size (Clear, Smoked Black, or Yellow) | 2–3 sheets | Easy to score and cut with an acrylic knife or laser cut. |
| **6.2** | **Standoff Kit** | M3 Brass/Nylon Standoffs & Screws Assortment (10mm, 15mm, 20mm M-F & F-F) | 1 box | Used for structural corners and stacking the dual-deck trays. |
| **6.3** | **Board Hardware** | M2.5 Screws, Nuts, and 5mm Spacers | 1 pack | Standard mounting hardware for Raspberry Pi and sensor breakouts. |
| **6.4** | **Connecting Wires** | 20cm Female-to-Female & Male-to-Female Dupont Jumper Wires (28 AWG) | 1 ribbon | For clean solderless connections between modules. |
| **6.5** | **CSI Ribbon Cable** | 15-pin to 15-pin (or 22-pin for Zero), 20cm–30cm flexible flat cable | 1 | Connects camera in head to the Pi body. |
