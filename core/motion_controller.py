"""
Project Alpha: Motion Controller & Kinematics Engine.
Controls Pan/Tilt neck servos (MG90S) with expressive gestures, and drives
the crawler tank tracks (DRV8833) with automatic table cliff detection.
Supports ESP32-S3 serial offload, native Pi 5 gpiozero, legacy RPi.GPIO,
and high-fidelity simulation / digital twin mode.
"""

import os
import glob
import time
import threading
from typing import Optional, Tuple, Dict, Any, List

from core.config import (
    IS_RASPBERRY_PI,
    PIN_SERVO_PAN, PIN_SERVO_TILT,
    PIN_MOTOR_LEFT_FWD, PIN_MOTOR_LEFT_REV,
    PIN_MOTOR_RIGHT_FWD, PIN_MOTOR_RIGHT_REV,
    PIN_CLIFF_LEFT, PIN_CLIFF_RIGHT,
    PIN_TOUCH_HEAD, PIN_CHARGE_DETECT,
    ESP32_SERIAL_PORT, ESP32_BAUD_RATE, MOTION_BACKEND
)
from core.arduino_bridge import ArduinoBridge


class MotionController:
    """Coordinates neck servos and crawler tracks with safety interlocks."""

    def __init__(
        self,
        hardware_enabled: bool = IS_RASPBERRY_PI,
        backend: Optional[str] = None
    ):
        self.hardware_enabled = hardware_enabled
        self.current_pan = 0.0    # -85.0 (Left) to +85.0 (Right)
        self.current_tilt = 0.0   # -25.0 (Down) to +35.0 (Up)
        self.driver_type = "sim"  # "serial_esp32", "gpiozero", "rpi_gpio", or "sim"
        self.bridge = ArduinoBridge.get_instance()

        # Non-blocking gesture state machine & cancellation
        self._gesture_lock = threading.Lock()
        self._gesture_thread: Optional[threading.Thread] = None
        self._cancel_gesture = threading.Event()

        # Non-blocking cliff evasion state machine & cancellation
        self._evasion_thread: Optional[threading.Thread] = None
        self._cancel_evasion = threading.Event()

        # Serial ESP32 handles & state
        self.serial_handle = None
        self.serial_port: Optional[str] = None
        self.serial_baud = ESP32_BAUD_RATE
        self.serial_lock = threading.Lock()
        self._esp32_cliff_left = False
        self._esp32_cliff_right = False
        self._esp32_wd = False
        self._esp32_last_telem = 0.0
        self._serial_running = False
        self._serial_rx_thread: Optional[threading.Thread] = None
        self._serial_ping_thread: Optional[threading.Thread] = None

        # RPi.GPIO / gpiozero handles
        self.pwm_pan = None
        self.pwm_tilt = None
        self.pwm_m_l_fwd = None
        self.pwm_m_l_rev = None
        self.pwm_m_r_fwd = None
        self.pwm_m_r_rev = None

        chosen_backend = (backend or MOTION_BACKEND or "auto").lower().strip()

        if chosen_backend == "sim":
            self.hardware_enabled = False
            self.driver_type = "sim"
            print("[MotionController] Simulation Mode explicitly requested.")
        elif self.hardware_enabled:
            self._init_backend(chosen_backend)
        else:
            self.driver_type = "sim"
            print("[MotionController] Simulation Mode active (Hardware disabled).")

    # =========================================================================
    # Backend Initialization (ESP32-S3 -> gpiozero -> RPi.GPIO -> Sim)
    # =========================================================================

    def _init_backend(self, requested_backend: str) -> None:
        """Initializes the motion driver according to requested backend or auto priority."""
        if requested_backend in ("serial_esp32", "esp32", "serial"):
            if self._init_serial_esp32():
                return
            print("[MotionController] Serial ESP32 init failed; falling back to simulation.")
            self.driver_type = "sim"
            self.hardware_enabled = False
            return

        if requested_backend == "gpiozero":
            if self._init_gpiozero():
                return
            print("[MotionController] gpiozero init failed; falling back to simulation.")
            self.driver_type = "sim"
            self.hardware_enabled = False
            return

        if requested_backend == "rpi_gpio":
            if self._init_rpi_gpio():
                return
            print("[MotionController] RPi.GPIO init failed; falling back to simulation.")
            self.driver_type = "sim"
            self.hardware_enabled = False
            return

        # Auto detection priority: serial_esp32 -> gpiozero -> rpi_gpio -> sim
        if self._init_serial_esp32():
            return
        if self._init_gpiozero():
            return
        if self._init_rpi_gpio():
            return

        print("[MotionController] All hardware drivers unavailable. Falling back to simulation.")
        self.driver_type = "sim"
        self.hardware_enabled = False

    def _init_serial_esp32(self, port: Optional[str] = None, baudrate: Optional[int] = None) -> bool:
        """Attempts connection to ESP32-S3 over USB CDC or UART serial."""
        target_port = port or ESP32_SERIAL_PORT
        target_baud = baudrate or self.serial_baud

        candidate_ports = []
        if target_port and target_port.lower() != "auto":
            candidate_ports.append(target_port)
        else:
            # Auto-scan common Linux / dev by-id patterns and Windows COM ports
            by_id = glob.glob("/dev/serial/by-id/*")
            candidate_ports.extend(by_id)
            for p in ["/dev/alpha_esp32", "/dev/ttyACM0", "/dev/ttyACM1", "/dev/ttyUSB0", "/dev/ttyUSB1"]:
                if os.path.exists(p) and p not in candidate_ports:
                    candidate_ports.append(p)
            # Add COM ports on Windows
            if os.name == "nt":
                for i in range(1, 21):
                    candidate_ports.append(f"COM{i}")

        if not candidate_ports:
            return False

        try:
            import serial
        except ImportError:
            print("[MotionController] 'pyserial' not installed; serial_esp32 driver unavailable.")
            return False

        for p in candidate_ports:
            try:
                ser = serial.Serial(p, target_baud, timeout=0.1, write_timeout=0.2)
                time.sleep(0.1)  # Brief settling
                self.serial_handle = ser
                self.serial_port = p
                self.driver_type = "serial_esp32"
                self._serial_running = True

                # Start background serial reader
                self._serial_rx_thread = threading.Thread(
                    target=self._serial_rx_worker,
                    daemon=True,
                    name="ESP32SerialRx"
                )
                self._serial_rx_thread.start()

                # Start background periodic ping heartbeat (5 Hz to keep 500ms watchdog alive)
                self._serial_ping_thread = threading.Thread(
                    target=self._serial_ping_worker,
                    daemon=True,
                    name="ESP32SerialPing"
                )
                self._serial_ping_thread.start()

                # Send initial ping to check link
                self._send_serial_cmd("P\n")
                print(f"[MotionController] ESP32-S3 Serial Controller connected on {p} @ {target_baud} baud.")
                return True
            except Exception:
                continue

        return False

    def _init_gpiozero(self) -> bool:
        """Initializes direct Pi 5 GPIO pins using gpiozero."""
        try:
            from gpiozero import PWMOutputDevice, DigitalInputDevice, AngularServo
            self.servo_pan = AngularServo(
                PIN_SERVO_PAN,
                min_angle=-85,
                max_angle=85,
                min_pulse_width=0.0006,
                max_pulse_width=0.0024
            )
            self.servo_tilt = AngularServo(
                PIN_SERVO_TILT,
                min_angle=-25,
                max_angle=35,
                min_pulse_width=0.0008,
                max_pulse_width=0.0022
            )
            self.servo_pan.angle = 0.0
            self.servo_tilt.angle = 0.0

            self.m_l_fwd = PWMOutputDevice(PIN_MOTOR_LEFT_FWD, frequency=1000)
            self.m_l_rev = PWMOutputDevice(PIN_MOTOR_LEFT_REV, frequency=1000)
            self.m_r_fwd = PWMOutputDevice(PIN_MOTOR_RIGHT_FWD, frequency=1000)
            self.m_r_rev = PWMOutputDevice(PIN_MOTOR_RIGHT_REV, frequency=1000)

            self.cliff_left = DigitalInputDevice(PIN_CLIFF_LEFT, pull_up=True)
            self.cliff_right = DigitalInputDevice(PIN_CLIFF_RIGHT, pull_up=True)
            self.touch_head = DigitalInputDevice(PIN_TOUCH_HEAD, pull_up=False)
            self.charge_detect = DigitalInputDevice(PIN_CHARGE_DETECT, pull_up=False)

            self.driver_type = "gpiozero"
            print("[MotionController] Raspberry Pi 5 Native GPIO Initialized (gpiozero/lgpio).")
            return True
        except Exception:
            return False

    def _init_rpi_gpio(self) -> bool:
        """Fallback: Legacy RPi.GPIO."""
        try:
            import RPi.GPIO as GPIO
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)

            GPIO.setup(PIN_SERVO_PAN, GPIO.OUT)
            GPIO.setup(PIN_SERVO_TILT, GPIO.OUT)
            self.pwm_pan = GPIO.PWM(PIN_SERVO_PAN, 50)
            self.pwm_tilt = GPIO.PWM(PIN_SERVO_TILT, 50)
            self.pwm_pan.start(self._angle_to_duty(0.0))
            self.pwm_tilt.start(self._angle_to_duty(0.0))

            for pin in [PIN_MOTOR_LEFT_FWD, PIN_MOTOR_LEFT_REV, PIN_MOTOR_RIGHT_FWD, PIN_MOTOR_RIGHT_REV]:
                GPIO.setup(pin, GPIO.OUT)

            self.pwm_m_l_fwd = GPIO.PWM(PIN_MOTOR_LEFT_FWD, 1000)
            self.pwm_m_l_rev = GPIO.PWM(PIN_MOTOR_LEFT_REV, 1000)
            self.pwm_m_r_fwd = GPIO.PWM(PIN_MOTOR_RIGHT_FWD, 1000)
            self.pwm_m_r_rev = GPIO.PWM(PIN_MOTOR_RIGHT_REV, 1000)

            for pwm in [self.pwm_m_l_fwd, self.pwm_m_l_rev, self.pwm_m_r_fwd, self.pwm_m_r_rev]:
                pwm.start(0)

            GPIO.setup(PIN_CLIFF_LEFT, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.setup(PIN_CLIFF_RIGHT, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.setup(PIN_TOUCH_HEAD, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
            GPIO.setup(PIN_CHARGE_DETECT, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

            self.driver_type = "rpi_gpio"
            print("[MotionController] Legacy RPi.GPIO Initialized.")
            return True
        except Exception:
            return False

    # =========================================================================
    # Serial Protocol Framing & Background Threads
    # =========================================================================

    @staticmethod
    def format_motor_cmd(left: float, right: float) -> str:
        """Formats normalized motor speeds (-1.00 to 1.00) into ASCII command."""
        clamped_l = max(-1.0, min(1.0, float(left)))
        clamped_r = max(-1.0, min(1.0, float(right)))
        return f"M {clamped_l:.2f} {clamped_r:.2f}\n"

    @staticmethod
    def format_head_cmd(pan_deg: float, tilt_deg: float) -> str:
        """Formats clamped pan/tilt degrees into ASCII command."""
        clamped_pan = max(-85.0, min(85.0, float(pan_deg)))
        clamped_tilt = max(-25.0, min(35.0, float(tilt_deg)))
        return f"H {clamped_pan:.1f} {clamped_tilt:.1f}\n"

    @staticmethod
    def parse_telem_line(line: str) -> Optional[Dict[str, int]]:
        """
        Parses incoming ESP32 telemetry frame:
        TELEM cliff_l=<0|1> cliff_r=<0|1> wd=<0|1>
        """
        raw = line.strip()
        if not raw.startswith("TELEM"):
            return None
        tokens = raw.split()[1:]
        data = {}
        for tok in tokens:
            if "=" in tok:
                k, v = tok.split("=", 1)
                try:
                    data[k.strip()] = int(v.strip())
                except ValueError:
                    pass
        return data if ("cliff_l" in data and "cliff_r" in data) else None

    def _send_serial_cmd(self, cmd_str: str) -> bool:
        """Thread-safe serial transmission to ESP32."""
        if not self.serial_handle or not self._serial_running:
            return False
        with self.serial_lock:
            try:
                self.serial_handle.write(cmd_str.encode("ascii"))
                self.serial_handle.flush()
                return True
            except Exception as e:
                print(f"[MotionController] Serial write error: {e}")
                return False

    def _serial_rx_worker(self) -> None:
        """Background thread reading asynchronous TELEM and ACK packets from ESP32."""
        while self._serial_running and self.serial_handle:
            try:
                line = self.serial_handle.readline().decode("ascii", errors="ignore").strip()
                if not line:
                    continue
                if line.startswith("TELEM"):
                    parsed = self.parse_telem_line(line)
                    if parsed:
                        self._esp32_cliff_left = bool(parsed.get("cliff_l", 0))
                        self._esp32_cliff_right = bool(parsed.get("cliff_r", 0))
                        self._esp32_wd = bool(parsed.get("wd", 0))
                        self._esp32_last_telem = time.time()
                elif line.startswith("ACK"):
                    pass
            except Exception:
                time.sleep(0.01)

    def _serial_ping_worker(self) -> None:
        """Background heartbeat ping thread (5 Hz) to maintain the ESP32 dead-man switch."""
        while self._serial_running and self.serial_handle:
            self._send_serial_cmd("P\n")
            time.sleep(0.20)

    def _angle_to_duty(self, angle: float) -> float:
        """Maps servo angle (-90 to +90) to standard 50Hz PWM duty cycle (2.5% to 12.5%)."""
        clamped = max(-90.0, min(90.0, angle))
        return 7.5 + (clamped / 90.0) * 2.5

    # =========================================================================
    # Neck Pan / Tilt Control
    # =========================================================================

    def set_head_pose(self, pan_deg: float, tilt_deg: float) -> None:
        """Sets neck pan (-85 to +85) and tilt (-25 to +35) angles."""
        self.current_pan = max(-85.0, min(85.0, float(pan_deg)))
        self.current_tilt = max(-25.0, min(35.0, float(tilt_deg)))

        if hasattr(self, "bridge") and self.bridge:
            self.bridge.set_head_pose(self.current_pan, self.current_tilt)

        if self.driver_type == "serial_esp32":
            self._send_serial_cmd(self.format_head_cmd(self.current_pan, self.current_tilt))
        elif self.hardware_enabled:
            if self.driver_type == "gpiozero" and hasattr(self, "servo_pan"):
                try:
                    self.servo_pan.angle = self.current_pan
                    self.servo_tilt.angle = self.current_tilt
                except Exception:
                    pass
            elif self.driver_type == "rpi_gpio" and self.pwm_pan and self.pwm_tilt:
                self.pwm_pan.ChangeDutyCycle(self._angle_to_duty(self.current_pan))
                self.pwm_tilt.ChangeDutyCycle(self._angle_to_duty(self.current_tilt))

    def is_head_touched(self) -> bool:
        """Returns True if the capacitive head touch sensor is being triggered."""
        if hasattr(self, "bridge") and self.bridge and not self.hardware_enabled:
            telem = self.bridge.get_telemetry()
            if telem.get("touch_active", False):
                return True

        if not self.hardware_enabled:
            return False
        if self.driver_type == "gpiozero" and hasattr(self, "touch_head"):
            return bool(self.touch_head.is_active)
        elif self.driver_type == "rpi_gpio":
            try:
                import RPi.GPIO as GPIO
                return GPIO.input(PIN_TOUCH_HEAD) == GPIO.HIGH
            except Exception:
                return False
        return False

    def is_dock_charging(self) -> bool:
        """Returns True if charging contact studs have engaged with the charging dock."""
        if hasattr(self, "bridge") and self.bridge and not self.hardware_enabled:
            telem = self.bridge.get_telemetry()
            if telem.get("charge_active", False):
                return True

        if not self.hardware_enabled:
            return False
        if self.driver_type == "gpiozero" and hasattr(self, "charge_detect"):
            return bool(self.charge_detect.is_active)
        elif self.driver_type == "rpi_gpio":
            try:
                import RPi.GPIO as GPIO
                return GPIO.input(PIN_CHARGE_DETECT) == GPIO.HIGH
            except Exception:
                return False
        return False

    # =========================================================================
    # Non-Blocking Gesture State Machine & Cancellation
    # =========================================================================

    def cancel_gesture(self) -> None:
        """Cancels any running non-blocking gesture immediately."""
        self._cancel_gesture.set()
        if self._gesture_thread and self._gesture_thread.is_alive():
            self._gesture_thread.join(timeout=0.25)

    def is_gesture_running(self) -> bool:
        """Returns True if a gesture is currently executing in the background."""
        return self._gesture_thread is not None and self._gesture_thread.is_alive()

    def wait_gesture(self, timeout: Optional[float] = None) -> bool:
        """Waits for current gesture to complete."""
        if self._gesture_thread and self._gesture_thread.is_alive():
            self._gesture_thread.join(timeout=timeout)
            return not self._gesture_thread.is_alive()
        return True

    def _dispatch_gesture(
        self,
        steps: List[Tuple[float, float, float]],
        orig_pan: Optional[float] = None,
        orig_tilt: Optional[float] = None,
        blocking: bool = False
    ) -> None:
        """
        Dispatches gesture steps [(pan, tilt, duration), ...] to background worker.
        Aborts gracefully if cancelled by a new gesture, cliff event, or stop().
        """
        self.cancel_gesture()
        self._cancel_gesture.clear()

        def _worker():
            try:
                for target_pan, target_tilt, duration in steps:
                    if self._cancel_gesture.is_set():
                        break
                    self.set_head_pose(target_pan, target_tilt)
                    if self._cancel_gesture.wait(timeout=duration):
                        break
            finally:
                if not self._cancel_gesture.is_set():
                    p = self.current_pan if orig_pan is None else orig_pan
                    t = self.current_tilt if orig_tilt is None else orig_tilt
                    self.set_head_pose(p, t)

        if blocking:
            _worker()
        else:
            self._gesture_thread = threading.Thread(
                target=_worker,
                daemon=True,
                name="MotionGestureWorker"
            )
            self._gesture_thread.start()

    def nod(self, repeats: int = 2, blocking: bool = False) -> None:
        """Expressive affirmative nod (non-blocking by default)."""
        orig_pan = self.current_pan
        orig_tilt = self.current_tilt
        steps = []
        for _ in range(repeats):
            steps.append((orig_pan, orig_tilt + 18.0, 0.12))
            steps.append((orig_pan, orig_tilt - 8.0, 0.12))
        self._dispatch_gesture(steps, orig_pan=orig_pan, orig_tilt=orig_tilt, blocking=blocking)

    def curious_tilt(self, blocking: bool = False) -> None:
        """Expressive Wall-E curious head tilt (non-blocking by default)."""
        orig_pan = self.current_pan
        orig_tilt = self.current_tilt
        steps = [(orig_pan + 15.0, orig_tilt + 18.0, 0.25)]
        self._dispatch_gesture(steps, orig_pan=None, orig_tilt=None, blocking=blocking)

    def head_shake(self, repeats: int = 2, blocking: bool = False) -> None:
        """Expressive side-to-side head shake (non-blocking by default)."""
        orig_pan = self.current_pan
        orig_tilt = self.current_tilt
        steps = []
        for _ in range(repeats):
            steps.append((orig_pan - 20.0, orig_tilt, 0.12))
            steps.append((orig_pan + 20.0, orig_tilt, 0.12))
        self._dispatch_gesture(steps, orig_pan=orig_pan, orig_tilt=orig_tilt, blocking=blocking)

    def excited_wiggle(self, blocking: bool = False) -> None:
        """Joyful rapid wiggle and double nod (non-blocking by default)."""
        orig_pan = self.current_pan
        orig_tilt = self.current_tilt
        steps = []
        for offset in [-12.0, 12.0, -12.0, 12.0, 0.0]:
            steps.append((orig_pan + offset, orig_tilt + 12.0, 0.08))
        self._dispatch_gesture(steps, orig_pan=orig_pan, orig_tilt=orig_tilt, blocking=blocking)

    def alert_recoil(self, blocking: bool = False) -> None:
        """Startled sudden head snap up and center (non-blocking by default)."""
        steps = [(0.0, 25.0, 0.20)]
        self._dispatch_gesture(steps, orig_pan=None, orig_tilt=None, blocking=blocking)

    def sad_droop(self, blocking: bool = False) -> None:
        """Slow melancholic head droop down (non-blocking by default)."""
        steps = [(self.current_pan, -22.0, 0.30)]
        self._dispatch_gesture(steps, orig_pan=None, orig_tilt=None, blocking=blocking)

    def confused_wobble(self, blocking: bool = False) -> None:
        """Quizzical asymmetrical head wobble (non-blocking by default)."""
        orig_pan = self.current_pan
        orig_tilt = self.current_tilt
        steps = [
            (orig_pan + 18.0, orig_tilt - 10.0, 0.15),
            (orig_pan - 14.0, orig_tilt + 15.0, 0.20)
        ]
        self._dispatch_gesture(steps, orig_pan=orig_pan, orig_tilt=orig_tilt, blocking=blocking)

    def head_pet_reaction(self, blocking: bool = False) -> None:
        """Loving reaction when head touch sensor is triggered (non-blocking by default)."""
        orig_pan = self.current_pan
        orig_tilt = self.current_tilt
        steps = [
            (orig_pan, 22.0, 0.20),
            (orig_pan, 22.0 + 18.0, 0.12),
            (orig_pan, 22.0 - 8.0, 0.12),
            (orig_pan, 22.0, 0.05)
        ]
        self._dispatch_gesture(steps, orig_pan=orig_pan, orig_tilt=orig_tilt, blocking=blocking)

    def express_emotion(self, emotion_str: str, blocking: bool = False) -> None:
        """Triggers appropriate physical head gesture matching an emotion."""
        emo = str(emotion_str).lower().replace("emotion.", "")
        if emo in ("happy", "idle"):
            self.nod(repeats=1, blocking=blocking)
        elif emo == "curious":
            self.curious_tilt(blocking=blocking)
        elif emo == "excited":
            self.excited_wiggle(blocking=blocking)
        elif emo in ("alert", "surprised"):
            self.alert_recoil(blocking=blocking)
        elif emo == "sad":
            self.sad_droop(blocking=blocking)
        elif emo == "confused":
            self.confused_wobble(blocking=blocking)
        elif emo == "love":
            self.head_pet_reaction(blocking=blocking)
        elif emo in ("angry", "skeptical", "squint"):
            self.head_shake(repeats=1, blocking=blocking)

    # =========================================================================
    # Crawler Locomotion & Table-Edge Safety
    # =========================================================================

    def check_cliff_sensors(self) -> bool:
        """Returns True if a table edge or drop is detected under front tracks."""
        if self.driver_type == "serial_esp32":
            return self._esp32_cliff_left or self._esp32_cliff_right

        if hasattr(self, "bridge") and self.bridge and not self.hardware_enabled:
            telem = self.bridge.get_telemetry()
            if telem.get("cliff_active", False):
                return True

        if not self.hardware_enabled:
            return False

        if self.driver_type == "gpiozero" and hasattr(self, "cliff_left"):
            # TCRT5000 output is LOW when reflection lost (cliff drop)
            left_drop = not self.cliff_left.is_active
            right_drop = not self.cliff_right.is_active
            return left_drop or right_drop

        if self.driver_type == "rpi_gpio":
            try:
                import RPi.GPIO as GPIO
                left_drop = GPIO.input(PIN_CLIFF_LEFT) == GPIO.LOW
                right_drop = GPIO.input(PIN_CLIFF_RIGHT) == GPIO.LOW
                return left_drop or right_drop
            except Exception:
                return False
        return False

    def get_cliff_status(self) -> Tuple[bool, bool]:
        """Returns (left_cliff, right_cliff) booleans."""
        if self.driver_type == "serial_esp32":
            return (self._esp32_cliff_left, self._esp32_cliff_right)
        if hasattr(self, "bridge") and self.bridge and not self.hardware_enabled:
            telem = self.bridge.get_telemetry()
            cliff = bool(telem.get("cliff_active", False))
            return (cliff, cliff)
        if not self.hardware_enabled:
            return (False, False)
        if self.driver_type == "gpiozero" and hasattr(self, "cliff_left"):
            return (not self.cliff_left.is_active, not self.cliff_right.is_active)
        if self.driver_type == "rpi_gpio":
            try:
                import RPi.GPIO as GPIO
                return (
                    GPIO.input(PIN_CLIFF_LEFT) == GPIO.LOW,
                    GPIO.input(PIN_CLIFF_RIGHT) == GPIO.LOW
                )
            except Exception:
                return (False, False)
        return (False, False)

    def cancel_cliff_evasion(self) -> None:
        """Cancels running emergency cliff evasion sequence."""
        self._cancel_evasion.set()
        if self._evasion_thread and self._evasion_thread.is_alive():
            self._evasion_thread.join(timeout=0.25)

    def is_cliff_evading(self) -> bool:
        """Returns True if emergency cliff evasion is actively executing."""
        return self._evasion_thread is not None and self._evasion_thread.is_alive()

    def _emergency_cliff_evasion(self, blocking: bool = False) -> None:
        """Reverses 5cm and spins 90 degrees away from edge non-blockingly."""
        self.cancel_gesture()
        self.cancel_cliff_evasion()
        self._cancel_evasion.clear()

        def _worker():
            try:
                # Step 1: Reverse for 0.4s
                self._apply_raw_drive(-0.6, -0.6)
                if self._cancel_evasion.wait(timeout=0.40):
                    return
                # Step 2: Spin turn for 0.5s
                self._apply_raw_drive(-0.6, 0.6)
                if self._cancel_evasion.wait(timeout=0.50):
                    return
            finally:
                self.stop()

        if blocking:
            _worker()
        else:
            self._evasion_thread = threading.Thread(
                target=_worker,
                daemon=True,
                name="CliffEvasionWorker"
            )
            self._evasion_thread.start()

    def _apply_raw_drive(self, left_speed: float, right_speed: float) -> None:
        """Applies motor outputs directly to hardware without recursive cliff checks."""
        clamped_l = max(-1.0, min(1.0, float(left_speed)))
        clamped_r = max(-1.0, min(1.0, float(right_speed)))

        if hasattr(self, "bridge") and self.bridge:
            self.bridge.drive(clamped_l, clamped_r)

        if self.driver_type == "serial_esp32":
            self._send_serial_cmd(self.format_motor_cmd(clamped_l, clamped_r))
        elif self.hardware_enabled:
            if self.driver_type == "gpiozero" and hasattr(self, "m_l_fwd"):
                self._apply_motor_gpiozero(self.m_l_fwd, self.m_l_rev, clamped_l)
                self._apply_motor_gpiozero(self.m_r_fwd, self.m_r_rev, clamped_r)
            elif self.driver_type == "rpi_gpio":
                self._apply_motor_pwm(self.pwm_m_l_fwd, self.pwm_m_l_rev, clamped_l)
                self._apply_motor_pwm(self.pwm_m_r_fwd, self.pwm_m_r_rev, clamped_r)

    def drive(self, left_speed: float, right_speed: float) -> None:
        """
        Drives tracks with normalized speeds (-1.0 to +1.0).
        Automatically interrupts forward motion if cliff edge is detected.
        """
        # Safety Interlock: Never drive forward off a cliff!
        if (left_speed > 0 or right_speed > 0) and self.check_cliff_sensors():
            print("[MotionController] CLIFF DETECTED! Emergency Brake!")
            self.stop()
            self._emergency_cliff_evasion(blocking=False)
            return

        # If currently evading a cliff and new forward command arrives, reject it
        if (left_speed > 0 or right_speed > 0) and self.is_cliff_evading():
            return

        # Stop active evasion if commanded backward or manual stop
        if left_speed <= 0 and right_speed <= 0 and self.is_cliff_evading():
            self.cancel_cliff_evasion()

        self._apply_raw_drive(left_speed, right_speed)

    def _apply_motor_gpiozero(self, dev_fwd, dev_rev, speed: float) -> None:
        clamped = max(-1.0, min(1.0, float(speed)))
        if clamped > 0:
            dev_fwd.value = clamped
            dev_rev.value = 0.0
        elif clamped < 0:
            dev_fwd.value = 0.0
            dev_rev.value = abs(clamped)
        else:
            dev_fwd.value = 0.0
            dev_rev.value = 0.0

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

    def forward(self, speed: float = 0.6) -> None:
        self.drive(speed, speed)

    def backward(self, speed: float = 0.6) -> None:
        self.drive(-speed, -speed)

    def turn_left(self, speed: float = 0.5) -> None:
        self.drive(-speed, speed)

    def turn_right(self, speed: float = 0.5) -> None:
        self.drive(speed, -speed)

    def stop(self) -> None:
        """Immediately halts crawler motors and cancels active evasion."""
        if hasattr(self, "_cancel_evasion"):
            self._cancel_evasion.set()
        if hasattr(self, "bridge") and self.bridge:
            self.bridge.stop()
        if self.driver_type == "serial_esp32":
            self._send_serial_cmd("S\n")
        self._apply_raw_drive(0.0, 0.0)

    def cleanup(self) -> None:
        """Stops all outputs and cleans up serial and GPIO resources safely."""
        self.cancel_gesture()
        self.cancel_cliff_evasion()
        self.stop()

        self._serial_running = False
        if self.serial_handle:
            try:
                self.serial_handle.close()
            except Exception:
                pass
            self.serial_handle = None

        if self.hardware_enabled:
            if self.driver_type == "gpiozero":
                for dev_name in [
                    "servo_pan", "servo_tilt", "m_l_fwd", "m_l_rev",
                    "m_r_fwd", "m_r_rev", "cliff_left", "cliff_right",
                    "touch_head", "charge_detect"
                ]:
                    if hasattr(self, dev_name):
                        try:
                            getattr(self, dev_name).close()
                        except Exception:
                            pass
            elif self.driver_type == "rpi_gpio":
                try:
                    import RPi.GPIO as GPIO
                    GPIO.cleanup()
                except Exception:
                    pass
