# Project Alpha: ESP32-S3 Mini Real-Time Motor, Servo & Cliff Controller

This firmware offloads all real-time, microsecond-critical hardware actuation from the Raspberry Pi 5 to a dedicated **ESP32-S3 Mini** (e.g. ESP32-S3-Zero, ESP32-S3-DevKitC-1, or SuperMini).

---

## 1. Verified ESP32-S3 GPIO Pinout Table

> [!IMPORTANT]
> The GPIOs below were selected specifically to avoid all ESP32-S3 hardware hazards:
> - **Strapping Pins Avoided**: GPIO 0 (boot mode), GPIO 3 (JTAG), GPIO 45 (VDD_SPI voltage), GPIO 46 (ROM log level).
> - **SPI Flash / PSRAM Avoided**: GPIO 33–37 (dedicated high-speed Octal SPI bus).
> - **Safe Logic Level**: All inputs and outputs operate at **3.3 V logic**.

| Peripheral | ESP32-S3 GPIO | Function / Signal | Mode | Notes |
| :--- | :---: | :--- | :--- | :--- |
| **DRV8833 Motor Driver** | **GPIO 4** | IN1 (Left Motor FWD) | Output (20 kHz PWM) | Silent ultrasonic PWM |
| **DRV8833 Motor Driver** | **GPIO 5** | IN2 (Left Motor REV) | Output (20 kHz PWM) | Silent ultrasonic PWM |
| **DRV8833 Motor Driver** | **GPIO 6** | IN3 (Right Motor FWD) | Output (20 kHz PWM) | Silent ultrasonic PWM |
| **DRV8833 Motor Driver** | **GPIO 7** | IN4 (Right Motor REV) | Output (20 kHz PWM) | Silent ultrasonic PWM |
| **MG90S Pan Servo** | **GPIO 8** | Neck Pan (Left/Right) | Output (50 Hz PWM) | Clamped to [-85°, +85°] |
| **MG90S Tilt Servo** | **GPIO 9** | Neck Tilt (Up/Down) | Output (50 Hz PWM) | Clamped to [-25°, +35°] |
| **TCRT5000 Left Cliff** | **GPIO 10** | D0 Table Edge Drop | Input (Pull-up) | Active LOW on drop |
| **TCRT5000 Right Cliff** | **GPIO 11** | D0 Table Edge Drop | Input (Pull-up) | Active LOW on drop |
| **Left Wheel Encoder** | **GPIO 12** | Phase A (PCNT Hook) | Input (Pull-up) | Optional wheel odometry |
| **Left Wheel Encoder** | **GPIO 13** | Phase B (PCNT Hook) | Input (Pull-up) | Optional wheel odometry |
| **Right Wheel Encoder**| **GPIO 14** | Phase A (PCNT Hook) | Input (Pull-up) | Optional wheel odometry |
| **Right Wheel Encoder**| **GPIO 15** | Phase B (PCNT Hook) | Input (Pull-up) | Optional wheel odometry |
| **Status / Watchdog LED**| **GPIO 2** | Link / Watchdog State| Output | On when Pi 5 link alive |
| **USB CDC Serial** | **GPIO 19 / 20** | USB D- / D+ | Native USB | `/dev/ttyACM0` on Pi 5 |
| *Alt Hardware UART* | **GPIO 43 / 44** | U0TXD / U0RXD | UART0 @ 115200 | For Pi 5 GPIO 14/15 UART |

---

## 2. Power & Electrical Wiring

```
                    ┌─────────────────────────┐
                    │   BUCK CONVERTER #1     │
                    │   (XL4015 or 5A UBEC)   │
                    │   Output: 5.1V @ 5A     │
                    └────────────┬────────────┘
                                 │
     ┌───────────────────────────┴───────────────────────────┐
     │ 5.1V                                                  │ 5.1V
     ▼                                                       ▼
┌──────────────┐                                       ┌──────────────┐
│Raspberry Pi 5│                                       │ ESP32-S3     │
│(Pins 2 & 4)  │                                       │ (5V / VBUS)  │
└──────┬───────┘                                       └──────┬───────┘
       │                                                      │
       │   USB-C Data Cable (/dev/ttyACM0 @ 115200 baud)      │
       └======================================================┘

                    ┌─────────────────────────┐
                    │   BUCK CONVERTER #2     │
                    │   (MP1584 5.5V-6.0V 2A) │
                    └────────────┬────────────┘
                                 │
     ┌───────────────────────────┴───────────────────────────┐
     ▼                                                       ▼
┌──────────────────┐                                   ┌──────────────┐
│DRV8833 VM (Motor)│                                   │MG90S Servos  │
│Crawler Tracks    │                                   │VCC (Red wire)│
└──────────────────┘                                   └──────────────┘

======================== COMMON GROUND (GND) ========================
All grounds (Pi 5, ESP32-S3, Buck #1, Buck #2, DRV8833, Servos)
MUST connect to the same common system GND.
```

> [!CAUTION]
> **TCRT5000 VCC Warning**: Power the TCRT5000 sensors from **3.3 V only** (ESP32 3V3 pin or Pi 5 Pin 1). Connecting VCC to 5 V causes the sensor D0 pin to output 5 V, which can damage the ESP32-S3 or Raspberry Pi 5 inputs.

---

## 3. Serial Communication Protocol

- **Baud Rate**: 115200 baud, 8N1
- **Framing**: ASCII, newline-terminated (`\n`)

### Pi 5 → ESP32-S3 Commands

| Command | Format | Example | Description |
| :--- | :--- | :--- | :--- |
| **Motor Drive** | `M <left> <right>\n` | `M 0.50 -0.50\n` | Normalized float speeds `[-1.00, 1.00]` |
| **Head Pose** | `H <pan> <tilt>\n` | `H 15.0 -10.0\n` | Pan `[-85, 85]`°, Tilt `[-25, 35]`° |
| **Emergency Stop**| `S\n` | `S\n` | Immediately zero motor outputs |
| **Heartbeat Ping**| `P\n` | `P\n` | Resets the 500 ms dead-man switch |

### ESP32-S3 → Pi 5 Responses

| Message | Format | Example | Description |
| :--- | :--- | :--- | :--- |
| **Acknowledge** | `ACK <cmd>\n` | `ACK M\n` | Confirms receipt and execution |
| **Telemetry** | `TELEM cliff_l=<0\|1> cliff_r=<0\|1> wd=<0\|1>\n` | `TELEM cliff_l=0 cliff_r=0 wd=0\n` | Broadcast at 10 Hz + immediately on cliff event |

- `cliff_l=1`: Left cliff sensor drop detected.
- `cliff_r=1`: Right cliff sensor drop detected.
- `wd=1`: Dead-man watchdog triggered (motors stopped due to lack of heartbeats).

---

## 4. Hardware Safety Reflexes

1. **Deterministic Cliff Brake (< 3 ms)**:
   The ESP32 runs a continuous 400 Hz hardware check on GPIO 10 and 11. If either pin drops LOW while forward motion is commanded, the firmware immediately brakes motor PWM to zero, executes a short 80 ms recoil, and emits an asynchronous `TELEM` line to the Pi 5.
2. **Dead-Man's Switch (500 ms)**:
   If the Pi 5 kernel freezes, crashes, or the USB connection drops for more than 500 ms, the ESP32 automatically cuts motor PWM to 0.

---

## 5. Building & Flashing

### Using PlatformIO (Recommended)

```bash
cd firmware/esp32_s3_motor_controller

# Compile firmware
pio run

# Flash to connected ESP32-S3
pio run --target upload

# Open Serial Monitor
pio device monitor --baud 115200
```

### Using Arduino IDE

1. Open Arduino IDE and select **Board: ESP32S3 Dev Module**.
2. Set **USB CDC On Boot**: *Enabled*.
3. Set **Flash Size**: *4MB or 8MB*.
4. Open `src/main.cpp` and click **Upload**.
