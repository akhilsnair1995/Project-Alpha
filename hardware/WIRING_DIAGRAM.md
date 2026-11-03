# Project Alpha: Wall-E Autonomous Desktop Rover - Electrical & Wiring Schematic

This document defines the power distribution architecture and the complete pin-to-pin wiring matrix between the Raspberry Pi, power rails, actuators, display, audio, and sensors.

---

## 1. Power Distribution & Dual-Rail Architecture

> [!CAUTION]
> **Brownout Prevention Rule**: Never power the MG90S servos or N20 DC gearmotors from the Raspberry Pi's 5V or 3.3V pins. Inductive motor spikes and high stall currents will cause the Raspberry Pi to reset or corrupt the MicroSD card. Always use the **Dual-Rail architecture** shown below with a common shared ground (`GND`).

```
                    ┌─────────────────────────────────┐
                    │  2S 18650 Pack (3500mAh / 25.9Wh)│
                    │      (7.4V Nominal / 8.4V Peak) │
                    └────────────────┬────────────────┘
                                    │
                               [Main Switch]
                                    │
           ┌────────────────────────┴────────────────────────┐
           │                                                 │
           ▼                                                 ▼
┌─────────────────────────┐                       ┌─────────────────────────┐
│   BUCK CONVERTER #1     │                       │   BUCK CONVERTER #2     │
│   (XL4015 or MP1584)    │                       │        (MP1584)         │
│   Output: 5.1V @ 3A-5A  │                       │   Output: 5.5V-6.0V @ 2A│
└──────────┬──────────────┘                       └──────────┬──────────────┘
           │                                                 │
           ▼ [LOGIC POWER RAIL]                              ▼ [MOTOR POWER RAIL]
 • Raspberry Pi 4 (Pins 2 & 4)                     • DRV8833 Motor Driver (VCC)
 • Waveshare 4G LTE Dongle                         • Pan Servo MG90S (Red wire)
 • 1.28" GC9A01 Round LCD (VCC)                    • Tilt Servo MG90S (Red wire)
 • MAX98357A Audio Amp (VIN)
 • INMP441 I2S Mic (VDD)
 • VL53L0X ToF & TCRT5000 Sensors (VCC)

========================== COMMON GROUND (GND) ==========================
       All GND lines from Battery, Bucks, Pi, Servos & Drivers MUST connect
```

---

## 2. Raspberry Pi 40-Pin GPIO Pinout Matrix

All GPIO assignments are designed to avoid peripheral hardware conflicts:

| Pin # | Pin Name | Peripheral | Module Pin | Function Description |
| :---: | :--- | :--- | :--- | :--- |
| **01** | **3.3V Power** | Sensors | VDD | Clean 3.3V logic reference (INMP441 / TTP223) |
| **02** | **5.0V Power** | Buck #1 Output | OUT+ (+5.1V) | Power input to Raspberry Pi |
| **03** | **GPIO 2 (SDA1)** | I2C Bus | SDA | Shared: VL53L0X (Distance) + ADS1115 (Battery ADC) |
| **04** | **5.0V Power** | Buck #1 Output | OUT+ (+5.1V) | Secondary 5.1V input (parallel for low resistance) |
| **05** | **GPIO 3 (SCL1)** | I2C Bus | SCL | Shared: VL53L0X (Distance) + ADS1115 (Battery ADC) |
| **06** | **GND** | System Ground | GND | Common ground reference |
| **07** | **GPIO 4** | Touch Sensor | OUT | TTP223 capacitive touch input (Head Petting) |
| **08** | **GPIO 14 (TXD)** | *Available* | — | Debug serial / expansion |
| **09** | **GND** | System Ground | GND | Common ground reference |
| **10** | **GPIO 15 (RXD)** | *Available* | — | Debug serial / expansion |
| **11** | **GPIO 17** | Cliff Sensor Left | D0 | TCRT5000 digital trigger (Active LOW on cliff drop) |
| **12** | **GPIO 18 (PCM_CLK)**| I2S Audio Bus | BCLK | Shared: MAX98357A (Amp) & INMP441 (Mic) bit clock |
| **13** | **GPIO 27** | Cliff Sensor Right| D0 | TCRT5000 digital trigger (Active LOW on cliff drop) |
| **14** | **GND** | System Ground | GND | Common ground reference |
| **15** | **GPIO 22** | LCD Display | DC | GC9A01 Data / Command selection pin |
| **16** | **GPIO 23** | LCD Display | RST | GC9A01 Hardware Reset pin |
| **17** | **3.3V Power** | *Spare* | — | Reserved |
| **18** | **GPIO 24** | LCD Display | BLK | GC9A01 Backlight control (PWM or high) |
| **19** | **GPIO 10 (MOSI)**| SPI0 Bus | DIN / MOSI | GC9A01 LCD pixel data input |
| **20** | **GND** | System Ground | GND | Common ground reference |
| **21** | **GPIO 9 (MISO)** | SPI0 Bus | *(Unused)* | MISO not required by display |
| **22** | **GPIO 25** | Pan Servo | PWM (Orange) | Neck Left/Right rotation servo control signal |
| **23** | **GPIO 11 (SCLK)**| SPI0 Bus | CLK / SCLK | GC9A01 LCD SPI Clock |
| **24** | **GPIO 8 (CE0)** | SPI0 Bus | CS (Left Eye) | Left Eye GC9A01 LCD Chip Select |
| **25** | **GND** | System Ground | GND | Common ground reference |
| **26** | **GPIO 7 (CE1)** | SPI0 Bus | CS (Right Eye)| Right Eye GC9A01 LCD Chip Select |
| **27** | **GPIO 0 (ID_SD)**| EEPROM / ID | — | Reserved |
| **28** | **GPIO 1 (ID_SC)**| EEPROM / ID | — | Reserved |
| **29** | **GPIO 5** | Tilt Servo | PWM (Orange) | Neck Up/Down tilt servo control signal |
| **30** | **GND** | System Ground | GND | Common ground reference |
| **31** | **GPIO 6** | Motor Driver | IN1 | DRV8833 Left Motor Forward (PWM) |
| **32** | **GPIO 12 (PWM0)** | Motor Driver | IN2 | DRV8833 Left Motor Reverse (PWM) |
| **33** | **GPIO 13 (PWM1)** | Motor Driver | IN3 | DRV8833 Right Motor Forward (PWM) |
| **34** | **GND** | System Ground | GND | Common ground reference |
| **35** | **GPIO 19 (PCM_FS)** | I2S Audio Bus | LRCLK / WS | Shared: MAX98357A (Amp) & INMP441 (Mic) Word Select |
| **36** | **GPIO 16** | Motor Driver | IN4 | DRV8833 Right Motor Reverse (PWM) |
| **37** | **GPIO 26** | *Available* | — | Spare GPIO (LED or buzzer) |
| **38** | **GPIO 20 (PCM_DIN)**| I2S Audio Bus | SD / DOUT | INMP441 Microphone data IN to Raspberry Pi |
| **39** | **GND** | System Ground | GND | Common ground reference |
| **40** | **GPIO 21 (PCM_DOUT)**| I2S Audio Bus| DIN | MAX98357A Speaker DAC data OUT from Raspberry Pi |

---

## 3. Subsystem Wiring Breakdown

### A. Dual GC9A01 1.28" Round Eye Displays (SPI)
Both screens share the high-speed SPI bus data and clock lines, but use independent Chip Select (`CS`) pins (`CE0` and `CE1`) to enable simultaneous or individual eye rendering (winks, independent squinting, or synchronized gaze):

```
Display Signal     Left Eye Module      Right Eye Module     Raspberry Pi Pin
--------------     ---------------      ----------------     ----------------
VCC          --->  VCC                  VCC             ---> Pin 2 or 4 (5.1V Rail)
GND          --->  GND                  GND             ---> Pin 20 (GND)
SCL (CLK)    --->  SCL                  SCL             ---> Pin 23 (GPIO 11 / SPI_CLK)
SDA (MOSI)   --->  SDA                  SDA             ---> Pin 19 (GPIO 10 / SPI_MOSI)
RES (RST)    --->  RES                  RES             ---> Pin 16 (GPIO 23 - Shared Reset)
DC           --->  DC                   DC              ---> Pin 15 (GPIO 22 - Shared Command/Data)
BLK          --->  BLK                  BLK             ---> Pin 18 (GPIO 24 - Shared Backlight)
CS           --->  CS (Left Only)       —               ---> Pin 24 (GPIO 8 / SPI_CE0)
CS           --->  —                    CS (Right Only) ---> Pin 26 (GPIO 7 / SPI_CE1)
```

### B. Audio System (I2S Mic & Amp)
Both modules share the bit clock (`BCLK`) and word select (`LRCLK`), but have separate data lines:
```
MAX98357A (Amp)       Raspberry Pi Pin
---------------       ----------------
VIN             --->  5.1V Logic Rail
GND             --->  Pin 14 (GND)
BCLK            --->  Pin 12 (GPIO 18)
LRC (LRCLK)     --->  Pin 35 (GPIO 19)
DIN             --->  Pin 40 (GPIO 21 / PCM_DOUT)
GAIN            --->  GND (Default +9dB gain)
SD              --->  Floating / Leave unconnected

INMP441 (Mic)         Raspberry Pi Pin
-------------         ----------------
VDD             --->  Pin 1 (3.3V)
GND             --->  Pin 39 (GND)
SCK (BCLK)      --->  Pin 12 (GPIO 18 - Shared)
WS (LRCLK)      --->  Pin 35 (GPIO 19 - Shared)
SD              --->  Pin 38 (GPIO 20 / PCM_DIN)
L/R             --->  GND (Left channel)
```

### C. Locomotion & Neck Actuators
```
DRV8833 Driver        Raspberry Pi / Power Rail
--------------        -------------------------
VM                    --->  Buck #2 OUT (+5.5V to 6V Motor Rail)
GND                   --->  Common System GND
IN1                   --->  Pin 31 (GPIO 6 - Left Forward)
IN2                   --->  Pin 32 (GPIO 12 - Left Reverse)
IN3                   --->  Pin 33 (GPIO 13 - Right Forward)
IN4                   --->  Pin 36 (GPIO 16 - Right Reverse)
OUT1 / OUT2           --->  Left N20 Motor terminals
OUT3 / OUT4           --->  Right N20 Motor terminals

MG90S Servos          Connection
------------          ----------
Pan Servo VCC (Red)   --->  Buck #2 OUT (+5.5V Motor Rail)
Pan Servo GND (Brown) --->  Common System GND
Pan Servo SIG (Orange)--->  Pin 22 (GPIO 25)

Tilt Servo VCC (Red)  --->  Buck #2 OUT (+5.5V Motor Rail)
Tilt Servo GND (Brown)--->  Common System GND
Tilt Servo SIG (Orange)-->  Pin 29 (GPIO 5)
```

### D. Desk Cliff Protection (TCRT5000 IR Modules)
```
Sensor Module         Raspberry Pi Pin
-------------         ----------------
Left TCRT5000 VCC --->  3.3V or 5.1V Logic Rail
Left TCRT5000 GND --->  System GND
Left TCRT5000 D0  --->  Pin 11 (GPIO 17)

Right TCRT5000 VCC--->  3.3V or 5.1V Logic Rail
Right TCRT5000 GND--->  System GND
Right TCRT5000 D0 --->  Pin 13 (GPIO 27)
```
*Note: Calibrate the onboard potentiometers on the TCRT5000 modules so the output pin goes HIGH when reflecting off the table surface, and drops LOW immediately when reaching a table edge.*
