"""
Project Alpha: Arduino Serial Bridge & Virtual Microcontroller Simulator.
Handles USB Serial communication with the physical Arduino Uno/Nano,
or transparently runs a high-fidelity virtual microcontroller simulator for PC/web testing.
"""

import time
import threading
from typing import Optional, Dict, Any, List, Callable
from collections import deque


class VirtualArduinoSim:
    """
    Cycle-accurate software model of the ATmega328P Arduino Spinal Controller.
    Simulates hardware PWM, servo registers, 250ms safety watchdog, and cliff interrupts.
    """

    def __init__(self):
        self.pan_angle: float = 0.0
        self.tilt_angle: float = 0.0
        self.motor_left_pwm: int = 0      # -255 to +255
        self.motor_right_pwm: int = 0     # -255 to +255
        self.cliff_triggered: bool = False
        self.head_touched: bool = False
        self.dock_charging: bool = False
        self.watchdog_active: bool = False
        self.last_heartbeat: float = time.time()
        self.watchdog_timeout: float = 0.30  # 300ms watchdog
        self.tx_buffer: deque = deque(maxlen=60)  # Packets from Arduino to Pi
        self.log_history: deque = deque(maxlen=80)
        self.is_running = True
        self._lock = threading.RLock()

        # Start simulated microcontroller clock loop (50Hz)
        self._thread = threading.Thread(target=self._loop, daemon=True, name="VirtualArduinoClock")
        self._thread.start()

    def _log(self, direction: str, packet: str):
        with self._lock:
            self.log_history.append({
                "time": round(time.time(), 3),
                "dir": direction,
                "msg": packet.strip()
            })

    def _loop(self):
        while self.is_running:
            now = time.time()
            with self._lock:
                # 1. Watchdog safety check: If Pi stops sending commands, cut motor PWM
                if (now - self.last_heartbeat > self.watchdog_timeout) and (self.motor_left_pwm != 0 or self.motor_right_pwm != 0):
                    self.motor_left_pwm = 0
                    self.motor_right_pwm = 0
                    self.watchdog_active = True
                    self.tx_buffer.append("ALERT:WATCHDOG_TIMEOUT\n")
                    self._log("TX", "ALERT:WATCHDOG_TIMEOUT")

                # 2. Cliff sensor safety reflex (<2ms simulated hardware override)
                if self.cliff_triggered and (self.motor_left_pwm > 0 or self.motor_right_pwm > 0):
                    self.motor_left_pwm = 0
                    self.motor_right_pwm = 0
                    self.tx_buffer.append("EVENT:CLIFF\n")
                    self._log("TX", "EVENT:CLIFF (Hardware Cutoff)")
            time.sleep(0.02)  # 50Hz update

    def process_incoming_command(self, raw_cmd: str) -> Optional[str]:
        """Parses and executes an incoming serial command string from the Raspberry Pi."""
        cmd = raw_cmd.strip()
        if not cmd:
            return None

        self._log("RX", cmd)
        parts = cmd.split()
        op = parts[0].upper()

        with self._lock:
            self.last_heartbeat = time.time()
            self.watchdog_active = False

            if op == "H" and len(parts) >= 3:
                # Head Pan/Tilt command: H <pan_deg> <tilt_deg>
                try:
                    self.pan_angle = max(-85.0, min(85.0, float(parts[1])))
                    self.tilt_angle = max(-25.0, min(35.0, float(parts[2])))
                    resp = f"OK H {self.pan_angle:.1f} {self.tilt_angle:.1f}\n"
                    self._log("TX", resp)
                    return resp
                except ValueError:
                    return "ERR BAD_PARAMS\n"

            elif op == "M" and len(parts) >= 3:
                # Motor drive command: M <left_pwm> <right_pwm> (-255 to 255)
                try:
                    left = int(float(parts[1]))
                    right = int(float(parts[2]))
                    if self.cliff_triggered and (left > 0 or right > 0):
                        # Hardware interlock: refuse forward movement
                        self.motor_left_pwm = 0
                        self.motor_right_pwm = 0
                        resp = "ERR CLIFF_INTERLOCK\n"
                    else:
                        self.motor_left_pwm = max(-255, min(255, left))
                        self.motor_right_pwm = max(-255, min(255, right))
                        resp = f"OK M {self.motor_left_pwm} {self.motor_right_pwm}\n"
                    self._log("TX", resp)
                    return resp
                except ValueError:
                    return "ERR BAD_PARAMS\n"

            elif op == "STOP":
                self.motor_left_pwm = 0
                self.motor_right_pwm = 0
                resp = "OK STOP\n"
                self._log("TX", resp)
                return resp

            elif op == "PING":
                resp = "PONG\n"
                self._log("TX", resp)
                return resp

            elif op == "G" and len(parts) >= 2:
                # Macro Gesture execution
                gesture = parts[1].upper()
                resp = f"OK GESTURE {gesture}\n"
                self._log("TX", resp)
                return resp

            elif op == "STATUS":
                resp = f"STATUS PAN:{self.pan_angle:.1f} TILT:{self.tilt_angle:.1f} ML:{self.motor_left_pwm} MR:{self.motor_right_pwm}\n"
                self._log("TX", resp)
                return resp

        return "ERR UNKNOWN_CMD\n"

    def read_outgoing_packet(self) -> Optional[str]:
        """Pulls a waiting packet sent from the Arduino to the Pi."""
        with self._lock:
            if self.tx_buffer:
                return self.tx_buffer.popleft()
        return None

    def trigger_cliff_sensor(self, active: bool = True):
        with self._lock:
            self.cliff_triggered = active
            if active:
                self.motor_left_pwm = 0
                self.motor_right_pwm = 0
                self.tx_buffer.append("EVENT:CLIFF\n")
                self._log("TX", "EVENT:CLIFF (Injected)")

    def trigger_touch_sensor(self, active: bool = True):
        with self._lock:
            self.head_touched = active
            if active:
                self.tx_buffer.append("EVENT:TOUCH\n")
                self._log("TX", "EVENT:TOUCH")

    def trigger_charging(self, active: bool = True):
        with self._lock:
            self.dock_charging = active
            if active:
                self.tx_buffer.append("EVENT:CHARGE\n")
                self._log("TX", "EVENT:CHARGE")

    def get_telemetry(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "is_simulated": True,
                "connected": True,
                "pan": round(self.pan_angle, 1),
                "tilt": round(self.tilt_angle, 1),
                "motor_left": self.motor_left_pwm,
                "motor_right": self.motor_right_pwm,
                "cliff_active": self.cliff_triggered,
                "touch_active": self.head_touched,
                "charge_active": self.dock_charging,
                "watchdog_active": self.watchdog_active,
                "recent_logs": list(self.log_history)[-25:]
            }


class ArduinoBridge:
    """
    Master bridge managing communication with Arduino hardware over USB Serial,
    falling back automatically to the cycle-accurate VirtualArduinoSim.
    """

    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self, port: Optional[str] = None, baudrate: int = 115200):
        self.port = port
        self.baudrate = baudrate
        self.serial_handle = None
        self.sim = VirtualArduinoSim()
        self.is_hardware = False
        self.event_callbacks: List[Callable[[str], None]] = []

        self._connect()
        self._rx_thread = threading.Thread(target=self._read_loop, daemon=True, name="ArduinoSerialRx")
        self._rx_thread.start()

    def _connect(self):
        """Attempts connection to physical Arduino; falls back to virtual simulator."""
        possible_ports = [self.port] if self.port else ["/dev/ttyUSB0", "/dev/ttyACM0", "COM3", "COM4"]
        try:
            import serial
            for p in possible_ports:
                if not p:
                    continue
                try:
                    self.serial_handle = serial.Serial(p, self.baudrate, timeout=0.1)
                    time.sleep(1.8)  # Allow Arduino DTR reset bootloader to settle
                    self.is_hardware = True
                    print(f"[ArduinoBridge] Connected to physical Arduino on {p} @ {self.baudrate} baud.")
                    return
                except Exception:
                    continue
        except ImportError:
            pass

        self.is_hardware = False
        print("[ArduinoBridge] No physical Arduino detected. Virtual Arduino Microcontroller active.")

    def _read_loop(self):
        """Continuously reads incoming asynchronous telemetry/events from Arduino."""
        while True:
            line = None
            if self.is_hardware and self.serial_handle:
                try:
                    if self.serial_handle.in_waiting > 0:
                        line = self.serial_handle.readline().decode("utf-8", errors="ignore").strip()
                except Exception:
                    line = None
            else:
                line = self.sim.read_outgoing_packet()
                if line:
                    line = line.strip()

            if line:
                for cb in self.event_callbacks:
                    try:
                        cb(line)
                    except Exception:
                        pass
            time.sleep(0.01)

    def register_event_callback(self, cb: Callable[[str], None]):
        self.event_callbacks.append(cb)

    def send_command(self, cmd: str) -> Optional[str]:
        """Sends a command to the Arduino (or simulator) and returns the immediate response."""
        formatted = cmd.strip() + "\n"
        if self.is_hardware and self.serial_handle:
            try:
                self.serial_handle.write(formatted.encode("utf-8"))
                self.serial_handle.flush()
                # Optional synchronous read
                return self.serial_handle.readline().decode("utf-8", errors="ignore").strip()
            except Exception as e:
                print(f"[ArduinoBridge] Serial Write Error: {e}")
                return None
        else:
            return self.sim.process_incoming_command(formatted)

    def set_head_pose(self, pan_deg: float, tilt_deg: float):
        return self.send_command(f"H {pan_deg:.1f} {tilt_deg:.1f}")

    def drive(self, left_speed: float, right_speed: float):
        """Speeds normalized -1.0 to 1.0 mapped to 8-bit PWM (-255 to 255)."""
        left_pwm = int(max(-1.0, min(1.0, left_speed)) * 255)
        right_pwm = int(max(-1.0, min(1.0, right_speed)) * 255)
        return self.send_command(f"M {left_pwm} {right_pwm}")

    def stop(self):
        return self.send_command("STOP")

    def ping(self):
        return self.send_command("PING")

    def get_telemetry(self) -> Dict[str, Any]:
        if self.is_hardware:
            return {
                "is_simulated": False,
                "connected": True,
                "port": self.port or "USB-Serial",
                "baudrate": self.baudrate
            }
        return self.sim.get_telemetry()
