"""
Project Alpha: Motion Controller & Kinematics Engine.
Controls Pan/Tilt neck servos (MG90S) with expressive gestures, and drives
the crawler tank tracks (DRV8833) with automatic table cliff detection.
"""

import time
from typing import Optional
from core.config import (
    IS_RASPBERRY_PI,
    PIN_SERVO_PAN, PIN_SERVO_TILT,
    PIN_MOTOR_LEFT_FWD, PIN_MOTOR_LEFT_REV,
    PIN_MOTOR_RIGHT_FWD, PIN_MOTOR_RIGHT_REV,
    PIN_CLIFF_LEFT, PIN_CLIFF_RIGHT
)

class MotionController:
    """Coordinates neck servos and crawler tracks with safety interlocks."""

    def __init__(self, hardware_enabled: bool = IS_RASPBERRY_PI):
        self.hardware_enabled = hardware_enabled
        self.current_pan = 0.0    # -85.0 (Left) to +85.0 (Right)
        self.current_tilt = 0.0   # -30.0 (Down) to +45.0 (Up)

        self.pwm_pan = None
        self.pwm_tilt = None
        self.pwm_m_l_fwd = None
        self.pwm_m_l_rev = None
        self.pwm_m_r_fwd = None
        self.pwm_m_r_rev = None

        if self.hardware_enabled:
            self._init_gpio()
        else:
            print("[MotionController] Simulation Mode active (Hardware GPIO disabled).")

    def _init_gpio(self) -> None:
        """Initializes RPi.GPIO pins and PWM channels."""
        try:
            import RPi.GPIO as GPIO
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)

            # Neck Servos (50Hz PWM)
            GPIO.setup(PIN_SERVO_PAN, GPIO.OUT)
            GPIO.setup(PIN_SERVO_TILT, GPIO.OUT)
            self.pwm_pan = GPIO.PWM(PIN_SERVO_PAN, 50)
            self.pwm_tilt = GPIO.PWM(PIN_SERVO_TILT, 50)
            self.pwm_pan.start(self._angle_to_duty(0.0))
            self.pwm_tilt.start(self._angle_to_duty(0.0))

            # Motor Driver Pins (DRV8833 - 1000Hz PWM)
            for pin in [PIN_MOTOR_LEFT_FWD, PIN_MOTOR_LEFT_REV, PIN_MOTOR_RIGHT_FWD, PIN_MOTOR_RIGHT_REV]:
                GPIO.setup(pin, GPIO.OUT)

            self.pwm_m_l_fwd = GPIO.PWM(PIN_MOTOR_LEFT_FWD, 1000)
            self.pwm_m_l_rev = GPIO.PWM(PIN_MOTOR_LEFT_REV, 1000)
            self.pwm_m_r_fwd = GPIO.PWM(PIN_MOTOR_RIGHT_FWD, 1000)
            self.pwm_m_r_rev = GPIO.PWM(PIN_MOTOR_RIGHT_REV, 1000)

            for pwm in [self.pwm_m_l_fwd, self.pwm_m_l_rev, self.pwm_m_r_fwd, self.pwm_m_r_rev]:
                pwm.start(0)

            # Cliff Sensors (TCRT5000 active LOW on cliff drop)
            GPIO.setup(PIN_CLIFF_LEFT, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.setup(PIN_CLIFF_RIGHT, GPIO.IN, pull_up_down=GPIO.PUD_UP)

            print("[MotionController] Hardware GPIO & Servos Initialized.")
        except Exception as e:
            print(f"[MotionController] GPIO Init Error: {e}. Falling back to simulation.")
            self.hardware_enabled = False

    def _angle_to_duty(self, angle: float) -> float:
        """Maps servo angle (-90 to +90) to standard 50Hz PWM duty cycle (2.5% to 12.5%)."""
        clamped = max(-90.0, min(90.0, angle))
        # -90 deg = 1ms (5.0%), 0 deg = 1.5ms (7.5%), +90 deg = 2ms (10.0%)
        return 7.5 + (clamped / 90.0) * 2.5

    # =========================================================================
    # Neck Pan / Tilt Control
    # =========================================================================

    def set_head_pose(self, pan_deg: float, tilt_deg: float) -> None:
        """Sets neck pan (-85 to +85) and tilt (-30 to +45) angles."""
        self.current_pan = max(-85.0, min(85.0, pan_deg))
        self.current_tilt = max(-30.0, min(45.0, tilt_deg))

        if self.hardware_enabled and self.pwm_pan and self.pwm_tilt:
            self.pwm_pan.ChangeDutyCycle(self._angle_to_duty(self.current_pan))
            self.pwm_tilt.ChangeDutyCycle(self._angle_to_duty(self.current_tilt))
        else:
            # Simulation feedback
            pass

    def nod(self, repeats: int = 2) -> None:
        """Expressive affirmative nod."""
        orig_tilt = self.current_tilt
        for _ in range(repeats):
            self.set_head_pose(self.current_pan, orig_tilt + 18)
            time.sleep(0.12)
            self.set_head_pose(self.current_pan, orig_tilt - 8)
            time.sleep(0.12)
        self.set_head_pose(self.current_pan, orig_tilt)

    def curious_tilt(self) -> None:
        """Expressive Wall-E curious head tilt."""
        self.set_head_pose(self.current_pan + 15, self.current_tilt + 18)
        time.sleep(0.25)

    def head_shake(self, repeats: int = 2) -> None:
        """Expressive side-to-side head shake (disagreement / confusion)."""
        orig_pan = self.current_pan
        for _ in range(repeats):
            self.set_head_pose(orig_pan - 20, self.current_tilt)
            time.sleep(0.12)
            self.set_head_pose(orig_pan + 20, self.current_tilt)
            time.sleep(0.12)
        self.set_head_pose(orig_pan, self.current_tilt)

    def excited_wiggle(self) -> None:
        """Joyful rapid wiggle and double nod."""
        orig_pan = self.current_pan
        orig_tilt = self.current_tilt
        for offset in [-12, 12, -12, 12, 0]:
            self.set_head_pose(orig_pan + offset, orig_tilt + 12)
            time.sleep(0.08)
        self.set_head_pose(orig_pan, orig_tilt)

    def alert_recoil(self) -> None:
        """Startled sudden head snap up and center."""
        self.set_head_pose(0.0, 25.0)
        time.sleep(0.2)

    def sad_droop(self) -> None:
        """Slow melancholic head droop down."""
        self.set_head_pose(self.current_pan, -22.0)
        time.sleep(0.3)

    def confused_wobble(self) -> None:
        """Quizzical asymmetrical head wobble."""
        orig_pan = self.current_pan
        orig_tilt = self.current_tilt
        self.set_head_pose(orig_pan + 18, orig_tilt - 10)
        time.sleep(0.15)
        self.set_head_pose(orig_pan - 14, orig_tilt + 15)
        time.sleep(0.2)
        self.set_head_pose(orig_pan, orig_tilt)

    def head_pet_reaction(self) -> None:
        """Loving reaction when head touch sensor is triggered or pet."""
        self.set_head_pose(self.current_pan, 22.0)
        time.sleep(0.2)
        self.nod(repeats=1)

    def express_emotion(self, emotion_str: str) -> None:
        """Triggers appropriate physical head gesture matching an emotion."""
        emo = str(emotion_str).lower().replace("emotion.", "")
        if emo in ("happy", "idle"):
            self.nod(repeats=1)
        elif emo == "curious":
            self.curious_tilt()
        elif emo == "excited":
            self.excited_wiggle()
        elif emo in ("alert", "surprised"):
            self.alert_recoil()
        elif emo == "sad":
            self.sad_droop()
        elif emo == "confused":
            self.confused_wobble()
        elif emo == "love":
            self.head_pet_reaction()
        elif emo in ("angry", "skeptical", "squint"):
            self.head_shake(repeats=1)

    # =========================================================================
    # Crawler Locomotion & Table-Edge Safety
    # =========================================================================

    def check_cliff_sensors(self) -> bool:
        """Returns True if a table edge or drop is detected under front tracks."""
        if not self.hardware_enabled:
            return False
        try:
            import RPi.GPIO as GPIO
            # TCRT5000 output is LOW when reflection lost (cliff detected)
            left_drop = GPIO.input(PIN_CLIFF_LEFT) == GPIO.LOW
            right_drop = GPIO.input(PIN_CLIFF_RIGHT) == GPIO.LOW
            return left_drop or right_drop
        except Exception:
            return False

    def drive(self, left_speed: float, right_speed: float) -> None:
        """
        Drives tracks with normalized speeds (-1.0 to +1.0).
        Automatically interrupts forward motion if cliff edge is detected.
        """
        # Safety Interlock: Never drive forward off a cliff!
        if (left_speed > 0 or right_speed > 0) and self.check_cliff_sensors():
            print("[MotionController] CLIFF DETECTED! Emergency Brake!")
            self.stop()
            self._emergency_cliff_evasion()
            return

        if self.hardware_enabled:
            self._apply_motor_pwm(self.pwm_m_l_fwd, self.pwm_m_l_rev, left_speed)
            self._apply_motor_pwm(self.pwm_m_r_fwd, self.pwm_m_r_rev, right_speed)

    def _apply_motor_pwm(self, pwm_fwd, pwm_rev, speed: float) -> None:
        duty = int(abs(speed) * 100)
        duty = max(0, min(100, duty))
        if speed > 0:
            pwm_fwd.ChangeDutyCycle(duty)
            pwm_rev.ChangeDutyCycle(0)
        elif speed < 0:
            pwm_fwd.ChangeDutyCycle(0)
            pwm_rev.ChangeDutyCycle(duty)
        else:
            pwm_fwd.ChangeDutyCycle(0)
            pwm_rev.ChangeDutyCycle(0)

    def _emergency_cliff_evasion(self) -> None:
        """Reverses 5cm and spins 90 degrees away from the edge."""
        if self.hardware_enabled:
            # Reverse for 0.4s
            self._apply_motor_pwm(self.pwm_m_l_fwd, self.pwm_m_l_rev, -0.6)
            self._apply_motor_pwm(self.pwm_m_r_fwd, self.pwm_m_r_rev, -0.6)
            time.sleep(0.4)
            # Spin turn
            self._apply_motor_pwm(self.pwm_m_l_fwd, self.pwm_m_l_rev, -0.6)
            self._apply_motor_pwm(self.pwm_m_r_fwd, self.pwm_m_r_rev, 0.6)
            time.sleep(0.5)
            self.stop()

    def forward(self, speed: float = 0.6) -> None:
        self.drive(speed, speed)

    def backward(self, speed: float = 0.6) -> None:
        self.drive(-speed, -speed)

    def turn_left(self, speed: float = 0.5) -> None:
        self.drive(-speed, speed)

    def turn_right(self, speed: float = 0.5) -> None:
        self.drive(speed, -speed)

    def stop(self) -> None:
        self.drive(0, 0)

    def cleanup(self) -> None:
        """Stops all PWM outputs safely."""
        self.stop()
        if self.hardware_enabled:
            try:
                import RPi.GPIO as GPIO
                GPIO.cleanup()
            except Exception:
                pass
