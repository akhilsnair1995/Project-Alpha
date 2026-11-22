"""
Project Alpha: System Configuration & Pinout Mappings.
Provides environment settings, GPIO assignments, and operational thresholds.
"""

import os
from pathlib import Path

# Base Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Auto-load local .env file if present
ENV_PATH = PROJECT_ROOT / ".env"
if ENV_PATH.exists():
    try:
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ[k.strip()] = v.strip().strip("'").strip('"')
    except Exception:
        pass

DB_PATH = DATA_DIR / "alpha_memory.db"
SNAPSHOTS_DIR = DATA_DIR / "snapshots"
SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)

# Authentic Alpha Voice Assets
ALPHA_VOICE_DIR = PROJECT_ROOT / "AlphaVoice"
ALPHA_VOICE_PATH = ALPHA_VOICE_DIR / "Voice 1.mp3"

# Hardware Platform Detection
_env_is_pi = os.environ.get("IS_RASPBERRY_PI")
if _env_is_pi is not None:
    IS_RASPBERRY_PI = _env_is_pi.strip().lower() in ("true", "1", "yes", "on")
else:
    IS_RASPBERRY_PI = False
    try:
        if os.path.exists("/proc/device-tree/model"):
            with open("/proc/device-tree/model", "r") as f:
                model = f.read().lower()
                if "raspberry pi" in model:
                    IS_RASPBERRY_PI = True
    except Exception:
        IS_RASPBERRY_PI = False

# Serial & ESP32-S3 Microcontroller Configuration
ESP32_SERIAL_PORT = os.environ.get("ESP32_SERIAL_PORT", "auto")
ESP32_BAUD_RATE = int(os.environ.get("ESP32_BAUD_RATE", "115200"))
MOTION_BACKEND = os.environ.get("MOTION_BACKEND", "auto")  # "auto", "serial_esp32", "gpiozero", "rpi_gpio", "sim"

# =============================================================================
# GPIO Pin Assignments (Matches hardware/WIRING_DIAGRAM.md)
# =============================================================================

# Neck Servos (MG90S)
PIN_SERVO_PAN = 25   # GPIO 25 (Pin 22) - Left/Right rotation
PIN_SERVO_TILT = 5   # GPIO 5  (Pin 29) - Up/Down tilt

# DRV8833 Dual H-Bridge Crawler Motors
PIN_MOTOR_LEFT_FWD = 6    # GPIO 6  (Pin 31) - IN1
PIN_MOTOR_LEFT_REV = 12   # GPIO 12 (Pin 32) - IN2
PIN_MOTOR_RIGHT_FWD = 13  # GPIO 13 (Pin 33) - IN3
PIN_MOTOR_RIGHT_REV = 16  # GPIO 16 (Pin 36) - IN4

# Safety & Touch Sensors
PIN_CLIFF_LEFT = 17       # GPIO 17 (Pin 11) - TCRT5000 Left Table Edge
PIN_CLIFF_RIGHT = 27      # GPIO 27 (Pin 13) - TCRT5000 Right Table Edge
PIN_TOUCH_HEAD = 4        # GPIO 4  (Pin 07) - TTP223 Capacitive Touch
PIN_CHARGE_DETECT = 26    # GPIO 26 (Pin 37) - Docking voltage sense

# Dual GC9A01 1.28" Round LCD Displays (SPI0)
SPI_BUS = 0
SPI_SPEED_HZ = 40_000_000  # 40MHz SPI clock
PIN_LCD_DC = 22           # GPIO 22 (Pin 15) - Shared Data/Command
PIN_LCD_RST = 23          # GPIO 23 (Pin 16) - Shared Reset
PIN_LCD_BLK = 24          # GPIO 24 (Pin 18) - Shared Backlight PWM
PIN_LCD_CS_LEFT = 8       # GPIO 8  (Pin 24) - CE0 Left Eye Chip Select
PIN_LCD_CS_RIGHT = 7      # GPIO 7  (Pin 26) - CE1 Right Eye Chip Select

# I2S Audio Bus (Shared bit clock & word select)
PIN_I2S_BCLK = 18         # GPIO 18 (Pin 12) - Bit Clock
PIN_I2S_LRCLK = 19        # GPIO 19 (Pin 35) - Word Select
PIN_I2S_MIC_DIN = 20      # GPIO 20 (Pin 38) - INMP441 Microphone Data In
PIN_I2S_SPK_DOUT = 21     # GPIO 21 (Pin 40) - MAX98357A Speaker Data Out

# =============================================================================
# AI & Conversational Settings
# =============================================================================

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
DEFAULT_GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")
GEMINI_FALLBACK_MODELS = [
    "gemini-3.5-flash",
    "gemini-3.6-flash",
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash-lite",
    "gemini-3.8-flash",
]
LOCAL_GEMMA_GGUF_PATH = os.environ.get(
    "LOCAL_GEMMA_PATH",
    str(DATA_DIR / "models" / "gemma-2-2b-it-Q4_K_M.gguf")
)

# Autonomous Roaming & Exploration Thresholds
CRITICAL_BATTERY_VOLTS = 6.80   # Docking trigger (~15% remaining)
FULL_BATTERY_VOLTS = 8.35       # Fully charged
ARUCO_DOCK_ID = 0               # Marker ID printed on charging dock
NOVELTY_SCORE_THRESHOLD = 0.65  # Triggers head inspection & photo capture
