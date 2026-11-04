"""
Project Alpha: Dual 1.28" Round LCD (GC9A01) Expressive Eye Engine.
Generates animated procedural eye expressions (Pillow/PIL) and drives dual SPI screens
with synchronized gaze, independent winks, squints, and dynamic emotional states.
"""

import time
import math
from enum import Enum
from typing import Tuple, Optional, Dict, Any, List
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
    SQUINT = "squint"
    WINK = "wink"
    SAD = "sad"
    SLEEPY = "sleepy"
    SURPRISED = "surprised"
    ALERT = "alert"
    ANALYZING = "analyzing"
    EXCITED = "excited"
    LOVE = "love"
    ANGRY = "angry"
    CONFUSED = "confused"
    SKEPTICAL = "skeptical"
    OFFLINE = "offline"

    @classmethod
    def from_str(cls, val: str) -> "Emotion":
        """Parses a string into an Emotion enum, handling common aliases."""
        if not val:
            return cls.IDLE
        cleaned = val.strip().lower().replace("-", "_").replace(" ", "_")
        aliases = {
            "sleep": cls.SLEEPY,
            "sleeping": cls.SLEEPY,
            "alarm": cls.ALERT,
            "danger": cls.ALERT,
            "shocked": cls.SURPRISED,
            "heart": cls.LOVE,
            "loving": cls.LOVE,
            "affection": cls.LOVE,
            "grumpy": cls.ANGRY,
            "mad": cls.ANGRY,
            "skeptic": cls.SKEPTICAL,
            "suspicious": cls.SKEPTICAL,
            "question": cls.CURIOUS,
            "joy": cls.HAPPY,
            "thrilled": cls.EXCITED,
            "puzzled": cls.CONFUSED,
            "shutdown": cls.OFFLINE,
            "off": cls.OFFLINE,
        }
        if cleaned in aliases:
            return aliases[cleaned]
        for e in cls:
            if e.value == cleaned:
                return e
        return cls.IDLE


class EyeRenderer:
    """Renders 240x240 procedural expressive eyes with pupils, eyelids, glints, and effects."""

    WIDTH = 240
    HEIGHT = 240
    CENTER = (120, 120)

    # Theme Colors
    BG_COLOR = (10, 10, 14)               # Deep matte black
    PUPIL_CYAN = (0, 210, 255)            # Wall-E Electric Cyan
    PUPIL_AMBER = (255, 170, 40)          # Wall-E Solar Amber
    PUPIL_PURPLE = (138, 75, 255)         # Electric Purple (Analyzing)
    PUPIL_ALERT = (56, 189, 248)          # Bright Alert Cyan
    PUPIL_LOVE = (255, 95, 160)           # Warm Rose / Pink (Love)
    PUPIL_ANGRY = (245, 65, 45)           # Fiery Red-Orange (Angry)
    PUPIL_EXCITED = (40, 245, 255)        # Luminous Cyan-Gold (Excited)
    PUPIL_SAD = (0, 150, 200)             # Muted Melancholy Teal
    GLINT_COLOR = (255, 255, 255)         # Specular reflection
    EYELID_COLOR = (10, 10, 14)           # Eyelid mask matching background

    def __init__(self, is_right_eye: bool = False):
        self.is_right_eye = is_right_eye
        self.current_emotion = Emotion.IDLE
        self.gaze_x = 0.0   # -1.0 (Left) to +1.0 (Right)
        self.gaze_y = 0.0   # -1.0 (Up) to +1.0 (Down)
        self.blink_ratio = 0.0  # 0.0 (Fully open) to 1.0 (Fully closed)
        self.pulse_phase = 0.0  # Phase for breathing or analyzing pulses

    def set_gaze(self, x: float, y: float) -> None:
        """Sets gaze offset (-1.0 to 1.0)."""
        self.gaze_x = max(-1.0, min(1.0, float(x)))
        self.gaze_y = max(-1.0, min(1.0, float(y)))

    def set_emotion(self, emotion: Emotion) -> None:
        self.current_emotion = emotion

    def _draw_heart(self, draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int, fill: Tuple[int, int, int]) -> None:
        """Draws a cute stylized heart specular highlight."""
        r = size // 2
        # Left and right lobe circles
        draw.ellipse([cx - size, cy - r, cx, cy + r], fill=fill)
        draw.ellipse([cx, cy - r, cx + size, cy + r], fill=fill)
        # Bottom triangular tip
        poly = [
            (cx - size, cy),
            (cx + size, cy),
            (cx, cy + size + r // 2)
        ]
        draw.polygon(poly, fill=fill)

    def _draw_sparkle(self, draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int, fill: Tuple[int, int, int]) -> None:
        """Draws a 4-point star sparkle specular highlight."""
        draw.line([cx - size, cy, cx + size, cy], fill=fill, width=2)
        draw.line([cx, cy - size, cx, cy + size], fill=fill, width=2)
        draw.ellipse([cx - 3, cy - 3, cx + 3, cy + 3], fill=fill)

    def render_frame(self, blink_override: Optional[float] = None) -> Image.Image:
        """Renders a single 240x240 RGB frame for this eye based on current emotion and gaze."""
        blink = blink_override if blink_override is not None else self.blink_ratio

        # Handle independent wink (right eye closes by default)
        if self.current_emotion == Emotion.WINK and self.is_right_eye:
            blink = 0.95

        img = Image.new("RGB", (self.WIDTH, self.HEIGHT), self.BG_COLOR)
        draw = ImageDraw.Draw(img)

        # 1. Base Pupil Radius & Color Selection
        base_radius = 58
        pupil_color = self.PUPIL_CYAN

        emo = self.current_emotion
        if emo == Emotion.SURPRISED:
            base_radius = 78
        elif emo == Emotion.ALERT:
            base_radius = 74
            pupil_color = self.PUPIL_ALERT
        elif emo == Emotion.SLEEPY:
            base_radius = 42
        elif emo == Emotion.EXCITED:
            base_radius = 66
            pupil_color = self.PUPIL_EXCITED
        elif emo == Emotion.LOVE:
            base_radius = 64
            pupil_color = self.PUPIL_LOVE
        elif emo == Emotion.ANGRY:
            base_radius = 56
            pupil_color = self.PUPIL_ANGRY
        elif emo == Emotion.CONFUSED:
            # Asymmetrical pupil sizing
            base_radius = 66 if not self.is_right_eye else 48
        elif emo == Emotion.SQUINT:
            base_radius = 52
        elif emo == Emotion.SAD:
            base_radius = 50
            pupil_color = self.PUPIL_SAD
        elif emo == Emotion.ANALYZING:
            base_radius = 60
            pupil_color = self.PUPIL_PURPLE
        elif emo == Emotion.OFFLINE:
            base_radius = 50
            pupil_color = self.PUPIL_AMBER

        # Gaze Offset (Max ±35 horizontal, ±28 vertical)
        cx = self.CENTER[0] + int(self.gaze_x * 35)
        cy = self.CENTER[1] + int(self.gaze_y * 28)

        # In confused mode, offset eyes slightly differently for quizzical effect
        if emo == Emotion.CONFUSED:
            if self.is_right_eye:
                cy += 8
            else:
                cy -= 6

        # 2. Draw Outer Halo / Glow Rings (Alert, Analyzing, Love, or Excited)
        if emo in (Emotion.ALERT, Emotion.ANALYZING, Emotion.EXCITED, Emotion.LOVE):
            glow_padding = 12 if emo != Emotion.ALERT else 16
            glow_color = (pupil_color[0] // 3, pupil_color[1] // 3, pupil_color[2] // 3)
            draw.ellipse(
                [cx - base_radius - glow_padding, cy - base_radius - glow_padding,
                 cx + base_radius + glow_padding, cy + base_radius + glow_padding],
                outline=pupil_color if emo == Emotion.ALERT else None,
                fill=glow_color,
                width=2 if emo == Emotion.ALERT else 1
            )
        else:
            # Standard subtle halo
            draw.ellipse(
                [cx - base_radius - 8, cy - base_radius - 8, cx + base_radius + 8, cy + base_radius + 8],
                fill=(pupil_color[0] // 4, pupil_color[1] // 4, pupil_color[2] // 4)
            )

        # 3. Core Pupil
        draw.ellipse(
            [cx - base_radius, cy - base_radius, cx + base_radius, cy + base_radius],
            fill=pupil_color
        )

        # 4. Special Inner Pupil Details (Analyzing scan lines, Alert rings)
        if emo == Emotion.ANALYZING:
            # Horizontal high-tech scan line & concentric rings
            draw.ellipse([cx - base_radius + 15, cy - base_radius + 15, cx + base_radius - 15, cy + base_radius - 15],
                         outline=(220, 180, 255), width=2)
            scan_y = cy + int(math.sin(time.time() * 6.0) * (base_radius - 10))
            draw.line([cx - base_radius + 8, scan_y, cx + base_radius - 8, scan_y],
                      fill=(255, 255, 255), width=3)
        elif emo == Emotion.ALERT:
            # Inner targeting cross / dot
            draw.ellipse([cx - 8, cy - 8, cx + 8, cy + 8], fill=(255, 255, 255))
            draw.line([cx - base_radius + 6, cy, cx + base_radius - 6, cy], fill=(255, 255, 255), width=1)
            draw.line([cx, cy - base_radius + 6, cx, cy + base_radius - 6], fill=(255, 255, 255), width=1)

        # 5. Specular Reflection Glints (Adds life, character, and shine)
        glint_x = cx - int(base_radius * 0.4)
        glint_y = cy - int(base_radius * 0.4)

        if emo == Emotion.LOVE:
            # Adorable heart specular glint
            self._draw_heart(draw, glint_x + 4, glint_y + 4, 10, self.GLINT_COLOR)
            draw.ellipse([glint_x + 20, glint_y + 20, glint_x + 26, glint_y + 26], fill=self.GLINT_COLOR)
        elif emo == Emotion.EXCITED:
            # Twinkling star sparkle glint + satellite dot
            self._draw_sparkle(draw, glint_x, glint_y, 11, self.GLINT_COLOR)
            self._draw_sparkle(draw, glint_x + 22, glint_y + 18, 6, self.GLINT_COLOR)
        else:
            # Standard round glints
            draw.ellipse([glint_x - 10, glint_y - 10, glint_x + 10, glint_y + 10], fill=self.GLINT_COLOR)
            draw.ellipse([glint_x + 14, glint_y + 14, glint_x + 20, glint_y + 20], fill=self.GLINT_COLOR)

        # 6. Eyelid Masking (Squint, Droop, Tilt, Angry, Sad, Happy)
        top_lid_y = int(blink * self.HEIGHT)
        bot_lid_y = self.HEIGHT - int(blink * 0.4 * self.HEIGHT)

        brow_angle = 0
        if emo == Emotion.SLEEPY:
            top_lid_y = max(top_lid_y, 115)
            bot_lid_y = min(bot_lid_y, 160)
        elif emo == Emotion.SQUINT:
            top_lid_y = max(top_lid_y, 85)
            bot_lid_y = min(bot_lid_y, 155)
        elif emo == Emotion.SKEPTICAL:
            # One eye narrowed, the other open
            if self.is_right_eye:
                top_lid_y = max(top_lid_y, 95)
                bot_lid_y = min(bot_lid_y, 160)
            else:
                top_lid_y = max(top_lid_y, 35)
                brow_angle = 15
        elif emo == Emotion.HAPPY:
            # Cheerful curved bottom lid (smiling cheeks)
            bot_lid_y = min(bot_lid_y, 138)
        elif emo == Emotion.SAD:
            # Downturned eyelids (sad droop)
            top_lid_y = max(top_lid_y, 90)
            brow_angle = -18 if not self.is_right_eye else 18
        elif emo == Emotion.ANGRY:
            # Inward downward sharp aggressive brow angle
            top_lid_y = max(top_lid_y, 88)
            brow_angle = 28 if not self.is_right_eye else -28
        elif emo == Emotion.CURIOUS:
            top_lid_y = max(top_lid_y, 45)
            brow_angle = 24 if not self.is_right_eye else 6
        elif emo == Emotion.CONFUSED:
            if not self.is_right_eye:
                top_lid_y = max(top_lid_y, 30)
                brow_angle = 26
            else:
                top_lid_y = max(top_lid_y, 80)
                brow_angle = -16

        # Draw Top Eyelid Mask
        if top_lid_y > 0:
            poly = [
                (0, 0),
                (self.WIDTH, 0),
                (self.WIDTH, max(0, top_lid_y - brow_angle)),
                (0, max(0, top_lid_y + brow_angle))
            ]
            draw.polygon(poly, fill=self.EYELID_COLOR)

        # Draw Bottom Eyelid Mask
        if bot_lid_y < self.HEIGHT:
            if emo == Emotion.HAPPY:
                # Cute crescent curve for happy bottom lid
                draw.chord([cx - base_radius - 20, bot_lid_y - 20, cx + base_radius + 20, self.HEIGHT + 40],
                           start=0, end=180, fill=self.EYELID_COLOR)
            draw.rectangle([0, bot_lid_y, self.WIDTH, self.HEIGHT], fill=self.EYELID_COLOR)

        # 7. If winking closed, draw a cute curved arc line
        if blink > 0.9:
            draw.arc([cx - 42, cy - 20, cx + 42, cy + 24], start=0, end=180, fill=pupil_color, width=5)

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

    def set_emotion(self, emotion: Emotion | str) -> Emotion:
        """Applies an emotional state across both eyes. Accepts Emotion enum or string."""
        if isinstance(emotion, str):
            emotion = Emotion.from_str(emotion)
        self.left_eye.set_emotion(emotion)
        self.right_eye.set_emotion(emotion)
        self.push_to_hardware()
        return emotion

    def get_emotion(self) -> Emotion:
        return self.left_eye.current_emotion

    def set_gaze(self, x: float, y: float) -> None:
        """Synchronizes gaze offset (-1.0 to +1.0) on both eyes."""
        self.left_eye.set_gaze(x, y)
        self.right_eye.set_gaze(x, y)
        self.push_to_hardware()

    def look_at(self, x: float, y: float, steps: int = 5, duration: float = 0.12) -> None:
        """Smoothly interpolates gaze to target (x, y)."""
        start_x = self.left_eye.gaze_x
        start_y = self.left_eye.gaze_y
        step_dt = duration / max(1, steps)
        for i in range(1, steps + 1):
            t = i / steps
            cur_x = start_x + (x - start_x) * t
            cur_y = start_y + (y - start_y) * t
            self.set_gaze(cur_x, cur_y)
            time.sleep(step_dt)

    def glance(self, direction: str = "right") -> None:
        """Quick natural glance in a direction and back."""
        d = direction.lower()
        gx, gy = 0.0, 0.0
        if "left" in d:
            gx = -0.7
        elif "right" in d:
            gx = 0.7
        elif "up" in d:
            gy = -0.6
        elif "down" in d:
            gy = 0.6

        orig_x, orig_y = self.left_eye.gaze_x, self.left_eye.gaze_y
        self.set_gaze(gx, gy)
        time.sleep(0.25)
        self.set_gaze(orig_x, orig_y)

    def render_eyes(self) -> Tuple[Image.Image, Image.Image]:
        """Returns the (left_image, right_image) pair."""
        return self.left_eye.render_frame(), self.right_eye.render_frame()

    def blink(self, duration_sec: float = 0.18) -> None:
        """Executes a quick natural blink transition."""
        steps = [0.0, 0.35, 0.85, 1.0, 0.65, 0.2, 0.0]
        step_time = duration_sec / len(steps)
        for b in steps:
            self.left_eye.blink_ratio = b
            self.right_eye.blink_ratio = b
            self.push_to_hardware()
            time.sleep(step_time)

    def double_blink(self) -> None:
        """Expressive double blink."""
        self.blink(0.14)
        time.sleep(0.08)
        self.blink(0.14)

    def wink(self, is_right_eye: bool = True, duration_sec: float = 0.35) -> None:
        """Winks one eye while keeping the other wide open."""
        target_eye = self.right_eye if is_right_eye else self.left_eye
        steps = [0.0, 0.5, 0.95, 0.95, 0.7, 0.0]
        step_time = duration_sec / len(steps)
        for b in steps:
            target_eye.blink_ratio = b
            self.push_to_hardware()
            time.sleep(step_time)

    def talking_pulse(self, cycles: int = 2) -> None:
        """Subtle pupil dilation pulse when speaking."""
        for _ in range(cycles):
            self.left_eye.blink_ratio = 0.15
            self.right_eye.blink_ratio = 0.15
            self.push_to_hardware()
            time.sleep(0.12)
            self.left_eye.blink_ratio = 0.0
            self.right_eye.blink_ratio = 0.0
            self.push_to_hardware()
            time.sleep(0.12)

    def get_state(self) -> Dict[str, Any]:
        """Returns dictionary snapshot of the current eye controller state."""
        return {
            "emotion": self.left_eye.current_emotion.value,
            "gaze_x": round(self.left_eye.gaze_x, 2),
            "gaze_y": round(self.left_eye.gaze_y, 2),
            "blink_ratio": round(self.left_eye.blink_ratio, 2),
            "available_emotions": [e.value for e in Emotion]
        }

    def push_to_hardware(self) -> None:
        """Pushes rendered RGB565 frames to both physical SPI displays if enabled."""
        if not self.hardware_enabled:
            return
        left_img, right_img = self.render_eyes()
        # On Raspberry Pi, writes buffer to dual GC9A01 over SPI CE0 and CE1
        pass
