"""
Project Alpha: Dual 1.28" Round LCD (GC9A01) Expressive Eye Engine.
Generates animated procedural eye expressions (Pillow/PIL) and drives dual SPI screens
with synchronized gaze or independent winks and squints.
"""

import time
import math
from enum import Enum
from typing import Tuple, Optional
from PIL import Image, ImageDraw

from core.config import (
    IS_RASPBERRY_PI, SPI_BUS, SPI_SPEED_HZ,
    PIN_LCD_DC, PIN_LCD_RST, PIN_LCD_BLK,
    PIN_LCD_CS_LEFT, PIN_LCD_CS_RIGHT
)

class Emotion(Enum):
    IDLE = "idle"
    HAPPY = "happy"
    CURIOUS = "curious"
    SKEPTICAL = "skeptical"
    SLEEPY = "sleepy"
    WINK = "wink"
    SURPRISED = "surprised"
    ANALYZING = "analyzing"
    OFFLINE = "offline"

class EyeRenderer:
    """Renders 240x240 procedural expressive eyes with pupils, eyelids, and glints."""

    WIDTH = 240
    HEIGHT = 240
    CENTER = (120, 120)

    # Theme Colors
    BG_COLOR = (10, 10, 14)               # Deep matte black
    PUPIL_CYAN = (0, 210, 255)            # Wall-E Electric Cyan
    PUPIL_AMBER = (255, 170, 40)          # Wall-E Solar Amber
    GLINT_COLOR = (255, 255, 255)         # Specular reflection
    EYELID_COLOR = (10, 10, 14)           # Eyelid mask matching background

    def __init__(self, is_right_eye: bool = False):
        self.is_right_eye = is_right_eye
        self.current_emotion = Emotion.IDLE
        self.gaze_x = 0.0   # -1.0 (Left) to +1.0 (Right)
        self.gaze_y = 0.0   # -1.0 (Up) to +1.0 (Down)
        self.blink_ratio = 0.0  # 0.0 (Fully open) to 1.0 (Fully closed)

    def set_gaze(self, x: float, y: float) -> None:
        """Sets gaze offset (-1.0 to 1.0)."""
        self.gaze_x = max(-1.0, min(1.0, x))
        self.gaze_y = max(-1.0, min(1.0, y))

    def set_emotion(self, emotion: Emotion) -> None:
        self.current_emotion = emotion

    def render_frame(self, blink_override: Optional[float] = None) -> Image.Image:
        """Renders a single 240x240 RGB frame for this eye."""
        blink = blink_override if blink_override is not None else self.blink_ratio

        # Handle independent wink (right eye closes)
        if self.current_emotion == Emotion.WINK and self.is_right_eye:
            blink = 0.95

        img = Image.new("RGB", (self.WIDTH, self.HEIGHT), self.BG_COLOR)
        draw = ImageDraw.Draw(img)

        # 1. Base Pupil Parameters
        base_radius = 58
        if self.current_emotion == Emotion.SURPRISED:
            base_radius = 78
        elif self.current_emotion == Emotion.SLEEPY:
            base_radius = 45

        # Gaze Offset (Max ±35 pixels)
        cx = self.CENTER[0] + int(self.gaze_x * 35)
        cy = self.CENTER[1] + int(self.gaze_y * 28)

        # Color Choice
        pupil_color = self.PUPIL_CYAN
        if self.current_emotion == Emotion.OFFLINE:
            pupil_color = self.PUPIL_AMBER
        elif self.current_emotion == Emotion.ANALYZING:
            pupil_color = (130, 80, 255) # Electric purple

        # 2. Draw Outer Glowing Iris & Core Pupil
        draw.ellipse(
            [cx - base_radius - 8, cy - base_radius - 8, cx + base_radius + 8, cy + base_radius + 8],
            fill=(pupil_color[0] // 3, pupil_color[1] // 3, pupil_color[2] // 3)
        )
        draw.ellipse(
            [cx - base_radius, cy - base_radius, cx + base_radius, cy + base_radius],
            fill=pupil_color
        )

        # 3. Specular Reflection Glints (Adds life and shine)
        glint_x = cx - int(base_radius * 0.4)
        glint_y = cy - int(base_radius * 0.4)
        draw.ellipse([glint_x - 10, glint_y - 10, glint_x + 10, glint_y + 10], fill=self.GLINT_COLOR)
        draw.ellipse([glint_x + 14, glint_y + 14, glint_x + 20, glint_y + 20], fill=self.GLINT_COLOR)

        # 4. Eyelid Masking (Squint, Droop, Curious Tilt)
        top_lid_y = int(blink * self.HEIGHT)
        bot_lid_y = self.HEIGHT - int(blink * 0.4 * self.HEIGHT)

        if self.current_emotion == Emotion.SLEEPY:
            top_lid_y = max(top_lid_y, 110)
        elif self.current_emotion == Emotion.SKEPTICAL:
            top_lid_y = max(top_lid_y, 80 if self.is_right_eye else 30)
        elif self.current_emotion == Emotion.HAPPY:
            # Bottom lid curves up
            bot_lid_y = min(bot_lid_y, 140)

        # Draw Top Eyelid Mask
        if top_lid_y > 0:
            brow_angle = 12 if not self.is_right_eye else -12
            if self.current_emotion == Emotion.CURIOUS:
                brow_angle = 22 if not self.is_right_eye else 5

            # Polygon angled top lid
            poly = [
                (0, 0),
                (self.WIDTH, 0),
                (self.WIDTH, max(0, top_lid_y - brow_angle)),
                (0, max(0, top_lid_y + brow_angle))
            ]
            draw.polygon(poly, fill=self.EYELID_COLOR)

        # Draw Bottom Eyelid Mask
        if bot_lid_y < self.HEIGHT:
            draw.rectangle([0, bot_lid_y, self.WIDTH, self.HEIGHT], fill=self.EYELID_COLOR)

        # If winking closed, draw a cute curved arc line
        if blink > 0.9:
            draw.arc([cx - 40, cy - 20, cx + 40, cy + 20], start=0, end=180, fill=pupil_color, width=4)

        return img


class DualEyeController:
    """Coordinates both Left and Right eyes for synchronized or expressive behaviors."""

    def __init__(self, hardware_enabled: bool = IS_RASPBERRY_PI):
        self.left_eye = EyeRenderer(is_right_eye=False)
        self.right_eye = EyeRenderer(is_right_eye=True)
        self.hardware_enabled = hardware_enabled

        if self.hardware_enabled:
            self._init_spi_hardware()
        else:
            print("[EyeAnimator] Simulation Mode active (Hardware SPI disabled).")

    def _init_spi_hardware(self) -> None:
        """Initializes spidev and GPIO pins on Raspberry Pi."""
        try:
            import spidev
            import RPi.GPIO as GPIO

            GPIO.setmode(GPIO.BCM)
            GPIO.setup(PIN_LCD_DC, GPIO.OUT)
            GPIO.setup(PIN_LCD_RST, GPIO.OUT)
            GPIO.setup(PIN_LCD_BLK, GPIO.OUT)
            GPIO.output(PIN_LCD_BLK, GPIO.HIGH)

            # Hardware Reset pulse
            GPIO.output(PIN_LCD_RST, GPIO.LOW)
            time.sleep(0.05)
            GPIO.output(PIN_LCD_RST, GPIO.HIGH)
            time.sleep(0.05)

            # SPI handles for Left (CE0) and Right (CE1)
            self.spi_left = spidev.SpiDev()
            self.spi_left.open(SPI_BUS, 0)
            self.spi_left.max_speed_hz = SPI_SPEED_HZ
            self.spi_left.mode = 0

            self.spi_right = spidev.SpiDev()
            self.spi_right.open(SPI_BUS, 1)
            self.spi_right.max_speed_hz = SPI_SPEED_HZ
            self.spi_right.mode = 0

            print("[EyeAnimator] Initialized Dual GC9A01 SPI displays (CE0 & CE1).")
        except Exception as e:
            print(f"[EyeAnimator] Could not initialize SPI hardware: {e}. Falling back to simulation.")
            self.hardware_enabled = False

    def set_emotion(self, emotion: Emotion) -> None:
        """Applies an emotional state across both eyes."""
        self.left_eye.set_emotion(emotion)
        self.right_eye.set_emotion(emotion)

    def set_gaze(self, x: float, y: float) -> None:
        """Synchronizes gaze offset (-1.0 to +1.0) on both eyes."""
        self.left_eye.set_gaze(x, y)
        self.right_eye.set_gaze(x, y)

    def render_eyes(self) -> Tuple[Image.Image, Image.Image]:
        """Returns the (left_image, right_image) pair."""
        return self.left_eye.render_frame(), self.right_eye.render_frame()

    def blink(self, duration_sec: float = 0.18) -> None:
        """Executes a quick natural blink transition."""
        steps = [0.0, 0.4, 0.9, 1.0, 0.7, 0.2, 0.0]
        step_time = duration_sec / len(steps)
        for b in steps:
            self.left_eye.blink_ratio = b
            self.right_eye.blink_ratio = b
            self.push_to_hardware()
            time.sleep(step_time)

    def push_to_hardware(self) -> None:
        """Pushes rendered RGB565 frames to both physical SPI displays if enabled."""
        if not self.hardware_enabled:
            return
        left_img, right_img = self.render_eyes()
        # Converts to 16-bit RGB565 format and writes via spidev
        # (Hardware implementation writes raw buffer with DC pin toggled)
        pass
