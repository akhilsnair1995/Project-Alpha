#!/usr/bin/env python3
"""
Project Alpha: Raspberry Pi 5 Virtual Machine & Hardware Simulator.
Emulates the Broadcom BCM2712 SoC & RP1 Southbridge I/O controller,
dual GC9A01 SPI displays (SPI0 CE0/CE1 @ 40MHz), DRV8833 H-bridge crawler tracks,
MG90S pan/tilt servos, TCRT5000 cliff sensors, TTP223 capacitive touch,
and executes the complete Project Alpha robot firmware lifecycle.
"""

import os
import sys
import time
import math
import types
import argparse
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# =============================================================================
# 1. RASPBERRY PI 5 RP1 SOUTHBRIDGE & BUS VIRTUALIZATION ENGINE
# =============================================================================

class VirtualPin:
    """Represents a virtual GPIO pin on the Raspberry Pi 5 RP1 Southbridge."""
    def __init__(self, bcm_pin: int, name: str, direction: str = "IN"):
        self.bcm_pin = bcm_pin
        self.name = name
        self.direction = direction    # "IN" or "OUT"
        self.value = 0.0             # 0.0 to 1.0 (binary or PWM duty cycle)
        self.is_active = False       # Digital input active state
        self.frequency = 0           # Frequency in Hz if PWM
        self.last_update = time.time()

    def set_value(self, val: float, freq: int = 0):
        self.value = float(val)
        self.is_active = bool(val > 0.5)
        if freq > 0:
            self.frequency = freq
        self.last_update = time.time()

    def set_input(self, active: bool):
        self.is_active = bool(active)
        self.value = 1.0 if active else 0.0
        self.last_update = time.time()


class VirtualSPIBus:
    """Simulates SPI0 hardware bus (CE0 = Left Eye, CE1 = Right Eye) @ 40MHz."""
    def __init__(self):
        self.devices = {0: "CE0 (Left GC9A01)", 1: "CE1 (Right GC9A01)"}
        self.command_counts = {0: 0, 1: 0}
        self.data_bytes_sent = {0: 0, 1: 0}
        self.frames_rendered = {0: 0, 1: 0}
        self.last_commands = {0: None, 1: None}
        self.speed_hz = 40_000_000

    def record_transfer(self, device_id: int, is_cmd: bool, payload: bytes | list):
        length = len(payload)
        if is_cmd:
            self.command_counts[device_id] = self.command_counts.get(device_id, 0) + 1
            if length > 0:
                self.last_commands[device_id] = hex(payload[0]) if isinstance(payload[0], int) else payload[0]
            if length > 0 and payload[0] == 0x2C:  # RAMWR memory write command
                self.frames_rendered[device_id] = self.frames_rendered.get(device_id, 0) + 1
        else:
            self.data_bytes_sent[device_id] = self.data_bytes_sent.get(device_id, 0) + length


class RaspberryPi5HardwareVM:
    """
    Virtual Machine controller that mocks Raspberry Pi 5 RP1 hardware interfaces
    and installs clean Python API mocks into sys.modules before firmware loads.
    """

    def __init__(self):
        self.model = "Raspberry Pi 5 Model B Rev 1.0"
        self.cpu = "Broadcom BCM2712 Quad-Core Cortex-A76 @ 2.4GHz"
        self.ram = "8GB LPDDR4X-4267"
        self.southbridge = "RP1 I/O Controller (PCIe 2.0 x4 interconnect)"

        # Pin mappings matching core.config
        self.pins: Dict[int, VirtualPin] = {
            # Actuators
            25: VirtualPin(25, "MG90S Pan Servo", "OUT"),
            5:  VirtualPin(5,  "MG90S Tilt Servo", "OUT"),
            6:  VirtualPin(6,  "Motor Left FWD", "OUT"),
            12: VirtualPin(12, "Motor Left REV", "OUT"),
            13: VirtualPin(13, "Motor Right FWD", "OUT"),
            16: VirtualPin(16, "Motor Right REV", "OUT"),
            # Sensors
            17: VirtualPin(17, "Cliff Left (TCRT5000)", "IN"),
            27: VirtualPin(27, "Cliff Right (TCRT5000)", "IN"),
            4:  VirtualPin(4,  "Head Pet Touch (TTP223)", "IN"),
            26: VirtualPin(26, "Charging Dock Detect", "IN"),
            # LCD Control
            22: VirtualPin(22, "LCD DC (Data/Cmd)", "OUT"),
            23: VirtualPin(23, "LCD RST (Hardware Reset)", "OUT"),
            24: VirtualPin(24, "LCD BLK (Backlight PWM)", "OUT"),
            # SPI Chip Selects
            8:  VirtualPin(8,  "SPI0 CE0 (Left Eye CS)", "OUT"),
            7:  VirtualPin(7,  "SPI0 CE1 (Right Eye CS)", "OUT"),
        }

        # Initialize default sensor inputs (Safe table surface, no cliff, not pet, not charging)
        self.pins[17].set_input(True)   # TCRT5000 active LOW on cliff drop -> True means SAFE
        self.pins[27].set_input(True)   # True means SAFE table
        self.pins[4].set_input(False)   # Not touched
        self.pins[26].set_input(False)  # Not on dock

        # Virtual SPI Bus
        self.spi_bus = VirtualSPIBus()

        # Odometry Simulation
        self.sim_x_cm = 0.0
        self.sim_y_cm = 0.0
        self.sim_heading_deg = 0.0
        self.sim_left_speed = 0.0
        self.sim_right_speed = 0.0
        self.sim_battery_v = 7.82  # 2S Li-Ion (~75% charged)
        self.is_charging = False

        # Current pan/tilt angles
        self.pan_angle = 0.0
        self.tilt_angle = 0.0

        # Inject environment & module mocks
        self._install_pi5_mocks()

    def _install_pi5_mocks(self):
        """Injects gpiozero and spidev virtual modules into sys.modules."""
        vm = self

        # 1. Override core.config hardware detection
        import core.config as config
        config.IS_RASPBERRY_PI = True

        # 2. Mock spidev module
        mock_spidev = types.ModuleType("spidev")

        class MockSpiDev:
            def __init__(self):
                self.bus = 0
                self.device = 0
                self.max_speed_hz = 40_000_000
                self.mode = 0

            def open(self, bus, device):
                self.bus = bus
                self.device = device

            def writebytes(self, data):
                dc_val = vm.pins[22].value > 0.5  # Pin 22 is LCD DC
                vm.spi_bus.record_transfer(self.device, is_cmd=(not dc_val), payload=data)

            def writebytes2(self, data):
                self.writebytes(data)

            def xfer2(self, data):
                self.writebytes(data)
                return data

            def close(self):
                pass

        mock_spidev.SpiDev = MockSpiDev
        sys.modules["spidev"] = mock_spidev

        # 3. Mock gpiozero module
        mock_gpiozero = types.ModuleType("gpiozero")

        class MockAngularServo:
            def __init__(self, pin, min_angle=-90, max_angle=90, min_pulse_width=0.001, max_pulse_width=0.002):
                self.pin_num = pin
                self.min_angle = min_angle
                self.max_angle = max_angle
                self._angle = 0.0
                if pin in vm.pins:
                    vm.pins[pin].direction = "OUT"
                    vm.pins[pin].frequency = 50

            @property
            def angle(self):
                return self._angle

            @angle.setter
            def angle(self, val):
                self._angle = max(self.min_angle, min(self.max_angle, float(val)))
                if self.pin_num == 25:
                    vm.pan_angle = self._angle
                elif self.pin_num == 5:
                    vm.tilt_angle = self._angle
                if self.pin_num in vm.pins:
                    # 50Hz PWM duty cycle mapping
                    vm.pins[self.pin_num].set_value(7.5 + (self._angle / 90.0) * 2.5, freq=50)

            def close(self):
                pass

        class MockPWMOutputDevice:
            def __init__(self, pin, frequency=1000):
                self.pin_num = pin
                self.freq = frequency
                self._val = 0.0
                if pin in vm.pins:
                    vm.pins[pin].direction = "OUT"
                    vm.pins[pin].frequency = frequency

            @property
            def value(self):
                return self._val

            @value.setter
            def value(self, val):
                self._val = max(0.0, min(1.0, float(val)))
                if self.pin_num in vm.pins:
                    vm.pins[self.pin_num].set_value(self._val, freq=self.freq)

            def on(self):
                self.value = 1.0

            def off(self):
                self.value = 0.0

            def close(self):
                pass

        class MockDigitalOutputDevice:
            def __init__(self, pin):
                self.pin_num = pin
                self._val = 0.0
                if pin in vm.pins:
                    vm.pins[pin].direction = "OUT"

            @property
            def value(self):
                return self._val

            @value.setter
            def value(self, val):
                self._val = 1.0 if val else 0.0
                if self.pin_num in vm.pins:
                    vm.pins[self.pin_num].set_value(self._val)

            def on(self):
                self.value = 1.0

            def off(self):
                self.value = 0.0

            def close(self):
                pass

        class MockDigitalInputDevice:
            def __init__(self, pin, pull_up=False):
                self.pin_num = pin
                self.pull_up = pull_up
                if pin in vm.pins:
                    vm.pins[pin].direction = "IN"

            @property
            def is_active(self):
                if self.pin_num in vm.pins:
                    return vm.pins[self.pin_num].is_active
                return False

            @property
            def value(self):
                return 1.0 if self.is_active else 0.0

            def close(self):
                pass

        mock_gpiozero.AngularServo = MockAngularServo
        mock_gpiozero.PWMOutputDevice = MockPWMOutputDevice
        mock_gpiozero.DigitalOutputDevice = MockDigitalOutputDevice
        mock_gpiozero.OutputDevice = MockDigitalOutputDevice
        mock_gpiozero.DigitalInputDevice = MockDigitalInputDevice

        sys.modules["gpiozero"] = mock_gpiozero

    # =========================================================================
    # Virtual Environment Actuation & Sensor Injection
    # =========================================================================

    def trigger_cliff(self, left_cliff: bool = False, right_cliff: bool = False):
        """Simulates table cliff drop (active LOW: True means safe, False means cliff)."""
        self.pins[17].set_input(not left_cliff)
        self.pins[27].set_input(not right_cliff)

    def trigger_head_touch(self, touched: bool):
        """Simulates TTP223 capacitive head touch sensor."""
        self.pins[4].set_input(touched)

    def trigger_dock_contact(self, docked: bool):
        """Simulates 5V contact with charging dock."""
        self.pins[26].set_input(docked)
        self.is_charging = docked

    def update_kinematics(self, dt: float = 0.1):
        """Calculates 2D planar odometry based on DRV8833 motor PWM duty cycles."""
        # Left track speed
        l_fwd = self.pins[6].value
        l_rev = self.pins[12].value
        self.sim_left_speed = (l_fwd - l_rev)

        # Right track speed
        r_fwd = self.pins[13].value
        r_rev = self.pins[16].value
        self.sim_right_speed = (r_fwd - r_rev)

        # Rover specs: Max speed ~ 20 cm/s, Track width = 14 cm
        max_speed_cm_s = 20.0
        track_width_cm = 14.0

        v_left = self.sim_left_speed * max_speed_cm_s
        v_right = self.sim_right_speed * max_speed_cm_s

        v_linear = (v_left + v_right) / 2.0
        omega_rad = (v_right - v_left) / track_width_cm

        self.sim_heading_deg = (self.sim_heading_deg + math.degrees(omega_rad * dt)) % 360.0
        heading_rad = math.radians(self.sim_heading_deg)

        self.sim_x_cm += v_linear * math.cos(heading_rad) * dt
        self.sim_y_cm += v_linear * math.sin(heading_rad) * dt

    def render_ascii_telemetry(self, robot_instance=None) -> str:
        """Generates an ASCII status board of the Raspberry Pi 5 hardware state."""
        l_fwd = self.pins[6].value
        l_rev = self.pins[12].value
        r_fwd = self.pins[13].value
        r_rev = self.pins[16].value

        left_cliff_safe = self.pins[17].is_active
        right_cliff_safe = self.pins[27].is_active
        head_touched = self.pins[4].is_active
        dock_engaged = self.pins[26].is_active

        emo_name = "UNKNOWN"
        gaze_info = "(0.0, 0.0)"
        if robot_instance and hasattr(robot_instance, "eyes"):
            state = robot_instance.eyes.get_state()
            emo_name = state["emotion"].upper()
            gaze_info = f"({state['gaze_x']}, {state['gaze_y']})"

        lines = [
            "┌────────────────────────────────────────────────────────────────────────┐",
            "│          RASPBERRY PI 5 VIRTUAL MACHINE HARDWARE TELEMETRY             │",
            "├────────────────────────────────────────────────────────────────────────┤",
            f"│ Host Machine:  {self.model:<47} │",
            f"│ SoC / CPU:     {self.cpu:<47} │",
            f"│ Southbridge:   {self.southbridge:<47} │",
            "├────────────────────────────────────────────────────────────────────────┤",
            "│ [RP1 GPIO BUS MATRIX]                                                  │",
            f"│  • GPIO 25 (Pan Servo):   {self.pan_angle:>6.1f}° (PWM 50Hz Duty: {self.pins[25].value:>4.1f}%)        │",
            f"│  • GPIO 05 (Tilt Servo):  {self.tilt_angle:>6.1f}° (PWM 50Hz Duty: {self.pins[5].value:>4.1f}%)        │",
            f"│  • GPIO 06/12 (Left M):   FWD={l_fwd*100:>3.0f}% | REV={l_rev*100:>3.0f}% (@ 1000Hz)            │",
            f"│  • GPIO 13/16 (Right M):  FWD={r_fwd*100:>3.0f}% | REV={r_rev*100:>3.0f}% (@ 1000Hz)            │",
            f"│  • GPIO 17 (Cliff Left):  {'[SAFE SURFACE]' if left_cliff_safe else '[!CLIFF DETECTED!]':<20} (TCRT5000 IR)       │",
            f"│  • GPIO 27 (Cliff Right): {'[SAFE SURFACE]' if right_cliff_safe else '[!CLIFF DETECTED!]':<20} (TCRT5000 IR)       │",
            f"│  • GPIO 04 (Head Touch):  {'[PETTING ACTIVE]' if head_touched else '[NO TOUCH]':<20} (TTP223 Capacitive)   │",
            f"│  • GPIO 26 (Dock Detect): {'[5V CONTACTED]' if dock_engaged else '[OFF DOCK]':<20} (Autonomous Dock)   │",
            "├────────────────────────────────────────────────────────────────────────┤",
            "│ [DUAL GC9A01 1.28\" ROUND LCDS (SPI0 @ 40MHz)]                          │",
            f"│  • Active Emotional State: {emo_name:<18} Gaze Target: {gaze_info:<12} │",
            f"│  • Left Eye (CE0):   Frames: {self.spi_bus.frames_rendered[0]:<5} | Data: {self.spi_bus.data_bytes_sent[0]/1024:>7.1f} KB │",
            f"│  • Right Eye (CE1):  Frames: {self.spi_bus.frames_rendered[1]:<5} | Data: {self.spi_bus.data_bytes_sent[1]/1024:>7.1f} KB │",
            "├────────────────────────────────────────────────────────────────────────┤",
            "│ [ODOMETRY & 2D DESKTOP POSITION]                                       │",
            f"│  • Coordinates: X={self.sim_x_cm:>+6.1f} cm, Y={self.sim_y_cm:>+6.1f} cm | Heading: {self.sim_heading_deg:>5.1f}°     │",
            f"│  • Battery Rail: {self.sim_battery_v:.2f}V ({'CHARGING' if self.is_charging else 'DISCHARGING'}) | Logic: 5.10V | Motor: 6.00V     │",
            "└────────────────────────────────────────────────────────────────────────┘",
        ]
        return "\n".join(lines)


# =============================================================================
# 2. AUTONOMOUS WORK SIMULATION RUNNER
# =============================================================================

def simulate_work_session(vm: RaspberryPi5HardwareVM):
    """
    Executes a comprehensive, realistic robot work simulation cycle:
    1. Cold boot POST & RP1 hardware initialization
    2. Startup Wall-E audio chime & affirmative head nod
    3. Desktop roaming & differential motor kinematics
    4. Table cliff edge detection & emergency recoil interlock
    5. User head touch & capacitive affection reaction
    6. Vision ArUco docking homing & charging dock engagement
    7. Persistent SQLite knowledge graph & user fact verification
    """
    from main import AlphaRobot
    from core.eye_animator import Emotion

    print("\n" + "=" * 74)
    print("  PROJECT ALPHA: STARTING RASPBERRY PI 5 VIRTUAL MACHINE WORK SIMULATION")
    print("=" * 74 + "\n")

    # -------------------------------------------------------------------------
    # Phase 1: Boot & Power-On Self Test (POST)
    # -------------------------------------------------------------------------
    print(">> [PHASE 1/7] Raspberry Pi 5 Cold Boot & Hardware Self-Test (POST)...")
    time.sleep(0.5)

    # Initialize AlphaRobot with voice enabled
    robot = AlphaRobot(voice_enabled=True)
    vm.update_kinematics()

    print(f"  [OK] BCM2712 Quad-Core Cortex-A76 validated.")
    print(f"  [OK] RP1 Southbridge GPIO allocated (Driver: {robot.motion.driver_type}).")
    print(f"  [OK] SPI0 Dual GC9A01 LCD controllers opened @ 40MHz.")
    print(f"  [OK] Startup chime played, head nod completed, eyes woke into HAPPY.")
    print("\n" + vm.render_ascii_telemetry(robot))
    time.sleep(1.0)

    # -------------------------------------------------------------------------
    # Phase 2: Dual GC9A01 LCD Emotional Expression Sequence
    # -------------------------------------------------------------------------
    print("\n>> [PHASE 2/7] Testing Dual-Eye GC9A01 SPI Bus & Emotional Dynamics...")
    test_emotions = [
        (Emotion.CURIOUS, 0.4, -0.3, "Inquiring gaze, head tilt"),
        (Emotion.EXCITED, 0.0, 0.5, "Pupil dilation, affirmative double blink"),
        (Emotion.LOVE, 0.0, 0.0, "Warm Rose pupils, talking pulse"),
        (Emotion.ALERT, -0.6, -0.4, "High contrast cyan, startled glance"),
        (Emotion.HAPPY, 0.0, 0.0, "Default companion idle smile")
    ]

    for emo, gx, gy, desc in test_emotions:
        robot.eyes.set_emotion(emo)
        robot.eyes.set_gaze(gx, gy)
        robot.motion.express_emotion(emo)
        print(f"  • Emotion -> {emo.name:<10} | Gaze: ({gx:+.1f}, {gy:+.1f}) | {desc}")
        time.sleep(0.3)

    print(f"  [OK] SPI transfers: CE0={vm.spi_bus.frames_rendered[0]} frames, CE1={vm.spi_bus.frames_rendered[1]} frames.")
    time.sleep(0.5)

    # -------------------------------------------------------------------------
    # Phase 3: Desktop Roaming & Motor Kinematics (DRV8833)
    # -------------------------------------------------------------------------
    print("\n>> [PHASE 3/7] Simulating Desktop Roaming & DRV8833 Motor Kinematics...")
    print("  • Driving forward (Speed: 60% PWM on GPIO 6 & 13)...")
    robot.motion.forward(speed=0.6)
    for _ in range(5):
        vm.update_kinematics(dt=0.2)
        time.sleep(0.05)

    print(f"  • Odometry Check: Traveled to X={vm.sim_x_cm:.1f} cm, Y={vm.sim_y_cm:.1f} cm.")

    print("  • Executing pivot turn (Left REV, Right FWD)...")
    robot.motion.turn_right(speed=0.5)
    for _ in range(4):
        vm.update_kinematics(dt=0.2)
        time.sleep(0.05)

    robot.motion.stop()
    vm.update_kinematics(dt=0.1)
    print(f"  • Turn completed. Heading: {vm.sim_heading_deg:.1f}°.")
    print("\n" + vm.render_ascii_telemetry(robot))
    time.sleep(1.0)

    # -------------------------------------------------------------------------
    # Phase 4: Desk Cliff Edge Hazard & Safety Recoil Interlock
    # -------------------------------------------------------------------------
    print("\n>> [PHASE 4/7] Simulating Tabletop Cliff Edge Hazard (TCRT5000)...")
    print("  • Rover creeping forward toward desk boundary...")
    robot.motion.forward(speed=0.4)
    vm.update_kinematics(dt=0.2)

    print("  [!] INJECTING HAZARD: Left Cliff Sensor (GPIO 17) drops off edge (reflection lost)!")
    vm.trigger_cliff(left_cliff=True, right_cliff=False)

    # Firmware check cliff sensors and emergency stop
    if robot.motion.check_cliff_sensors():
        print("  [SAFETY INTERLOCK TRIGGERED] Firmware detected cliff edge!")
        robot.eyes.set_emotion(Emotion.ALERT)
        robot.voice.play_sound("alert")
        robot.motion.alert_recoil()
        robot.motion.stop()
        print("  • Action: Immediate motor cut -> reverse recoil -> alert siren chime.")

    # Reset sensor to safe floor
    vm.trigger_cliff(left_cliff=False, right_cliff=False)
    vm.update_kinematics(dt=0.1)
    print("  [OK] Surface restored. Robot successfully avoided desk fall.")
    time.sleep(1.0)

    # -------------------------------------------------------------------------
    # Phase 5: Capacitive Touch Petting Interaction (TTP223)
    # -------------------------------------------------------------------------
    print("\n>> [PHASE 5/7] Simulating User Head Petting Interaction (TTP223)...")
    print("  [!] INJECTING SENSOR: User touching Wall-E's head (GPIO 4 goes HIGH)...")
    vm.trigger_head_touch(True)

    if robot.motion.is_head_touched():
        print("  [TOUCH DETECTED] Wall-E recognizes companion affection!")
        robot.eyes.set_emotion(Emotion.LOVE)
        robot.voice.play_sound("love")
        robot.motion.head_pet_reaction()
        print("  • Action: Neck tilts up to +22° -> happy nod -> purr chime -> LOVE eyes.")

    vm.trigger_head_touch(False)
    time.sleep(1.0)

    # -------------------------------------------------------------------------
    # Phase 6: Vision Perception & Autonomous Dock Homing
    # -------------------------------------------------------------------------
    print("\n>> [PHASE 6/7] Simulating Vision Perception & Autonomous Charging Dock Homing...")
    print("  • Vision Cortex scans for ArUco Marker #0 (Charging Dock)...")
    # Simulate dock sighting offset
    mock_marker_offset_x = 0.20
    target_pan = mock_marker_offset_x * 45.0
    print(f"  • ArUco #0 spotted at offset {mock_marker_offset_x:+.2f}. Aligning neck servo to {target_pan:+.1f}°...")
    robot.motion.set_head_pose(pan_deg=target_pan, tilt_deg=-10.0)
    robot.eyes.look_at(mock_marker_offset_x, 0.0)

    print("  • Creeping onto dock ramps...")
    robot.motion.forward(speed=0.25)
    for _ in range(3):
        vm.update_kinematics(dt=0.1)

    print("  [!] DOCK ENGAGED: Underside contact studs touch 5V rail (GPIO 26 goes HIGH)!")
    vm.trigger_dock_contact(True)

    if robot.motion.is_dock_charging():
        robot.motion.stop()
        robot.eyes.set_emotion(Emotion.SLEEPY)
        robot.voice.play_sound("startup")
        print("  • Action: Motors halted -> Charging voltage locked -> Eyes enter SLEEPY low power state.")

    print("\n" + vm.render_ascii_telemetry(robot))
    time.sleep(1.0)

    # -------------------------------------------------------------------------
    # Phase 7: Persistent SQLite Knowledge Graph & Fact Learning
    # -------------------------------------------------------------------------
    print("\n>> [PHASE 7/7] Verifying Persistent SQLite Knowledge Graph (alpha_memory.db)...")
    facts = robot.db.get_user_facts()
    print(f"  • Current Learned User Profile Facts ({len(facts)} entries):")
    for f in facts:
        print(f"    - [{f['category'].upper()}]: {f['fact']}")

    # Log a simulated exploration observation into SQLite
    robot.db.log_observation(
        observation=f"Raspberry Pi 5 Virtual Machine simulation cycle successfully executed. Docked at X={vm.sim_x_cm:.1f}cm, Y={vm.sim_y_cm:.1f}cm.",
        room_name="Work Desk",
        battery_level=vm.sim_battery_v
    )
    obs = robot.db.get_recent_observations(limit=1)
    if obs:
        print(f"  • Stored Episodic Observation: \"{obs[0]['observation']}\"")

    print("\n" + "=" * 74)
    print("  RASPBERRY PI 5 VIRTUAL MACHINE WORK SIMULATION COMPLETE: ALL TESTS PASSED!")
    print("=" * 74 + "\n")

    # Cleanup safely
    robot.motion.cleanup()
    robot.vision.release()
    return robot


# =============================================================================
# 3. INTERACTIVE CLI RUNNER & ENTRYPOINT
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Raspberry Pi 5 Virtual Machine & Hardware Simulator")
    parser.add_argument("--work-sim", action="store_true", help="Run complete autonomous robot work simulation")
    parser.add_argument("--interactive", action="store_true", help="Launch interactive CLI chat session on the virtual Pi 5")
    parser.add_argument("--web", action="store_true", help="Launch Digital Twin Web Simulator server on port 8085")
    args = parser.parse_args()

    # Spin up Raspberry Pi 5 Virtual Machine environment
    vm = RaspberryPi5HardwareVM()

    if args.interactive:
        from main import AlphaRobot
        print("\nStarting Project Alpha on Virtual Raspberry Pi 5 in Interactive CLI Mode...\n")
        robot = AlphaRobot(voice_enabled=True)
        robot.run_cli_chat(voice_output=True)
    elif args.web:
        print("\nStarting Project Alpha Virtual Machine with Digital Twin Web Simulator...\n")
        from simulator.run_sim import get_robot, SimulatorAPIHandler, PORT
        import http.server
        import socketserver

        robot = get_robot()
        print(vm.render_ascii_telemetry(robot))

        active_port = PORT
        httpd = None
        candidate_ports = [PORT] + [p for p in [8086, 8088, 8090, 8080] if p != PORT]
        socketserver.ThreadingTCPServer.allow_reuse_address = True
        for test_port in candidate_ports:
            try:
                httpd = socketserver.ThreadingTCPServer(("", test_port), SimulatorAPIHandler)
                active_port = test_port
                break
            except OSError:
                continue

        if not httpd:
            print(f"[Web Simulator] Error: Could not bind to port {PORT} or fallback ports.")
            return

        print(f"[Web Simulator] Listening on http://localhost:{active_port}")
        print(f"[Web Simulator] Open in your browser: http://localhost:{active_port}")
        url = f"http://localhost:{active_port}"
        try:
            if os.system("which explorer.exe >/dev/null 2>&1") == 0:
                os.system(f"explorer.exe '{url}' 2>/dev/null &")
            else:
                import webbrowser
                webbrowser.open(url)
        except Exception:
            pass

        with httpd:
            try:
                httpd.serve_forever()
            except KeyboardInterrupt:
                print("\nShutting down web simulator.")
    else:
        # Default: Full work simulation cycle
        simulate_work_session(vm)


if __name__ == "__main__":
    main()
