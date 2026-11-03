# Wall-E Digital Twin Simulator

Interactive hardware and behavioral simulator for **Project Alpha: Wall-E Autonomous Desktop Rover**.

---

## What is Included

1. **Tabletop Roam Arena & Kinematics**:
   - **Locomotion**: Differential drive tank tracks with forward, reverse, pivot turns, and 360° spin.
   - **Keyboard Controls**: `W` (Forward), `S` (Reverse), `A` (Spin Left), `D` (Spin Right), `Space` (Emergency Stop).
   - **Pan / Tilt Servos**: MG90S head control (-85° to +85° Pan on GPIO 25, -30° to +40° Tilt on GPIO 5).
   - **Desk Cliff Edge Detection**: Real-time simulation of TCRT5000 IR reflectance sensors on the front left & right. The rover detects table edges and executes emergency halts.
   - **Obstacle Proximity (VL53L0X ToF Laser)**: Dynamic raycasting against draggable obstacles in the arena.
   - **Autonomous Roam Mode**: Closed-loop obstacle avoidance and desk edge safety navigation.
   - **Dual GC9A01 1.28" Round LCD Eye Displays**: Live animated expressions (Curious, Happy, Squint, Wink, Sad, Sleep, Alert).
   - **Head Petting (TTP223)**: Interactive capacitive touch petting reaction.

2. **Interactive Live Wiring Schematic**:
   - Raspberry Pi 40-pin GPIO pinout matrix with signal types (5V, 3.3V, GND, SPI, I2C, I2S, PWM).
   - Dual-rail power architecture (Buck #1 5.1V logic vs Buck #2 6.0V motor rail).
   - Click any pin or module card to trace wire routes and verify connections.

---

## How to Run

### Method 1: Direct in Browser (Zero Install)
Simply double-click or open [index.html](file:///c:/Users/akhil/AI%20Playground/Project%20Alpha/simulator/index.html) in any web browser (Chrome, Edge, Firefox).

### Method 2: Via Python Launcher
Run in terminal:
```bash
python simulator/run_sim.py
```
This serves the simulator on `http://localhost:8085` and automatically opens your browser.
