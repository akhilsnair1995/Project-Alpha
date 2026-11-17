"""
Unit Tests for Raspberry Pi 5 Virtual Machine & Hardware Bus Emulation.
Verifies RP1 Southbridge GPIO mapping, SPI0 dual GC9A01 LCD controllers,
differential kinematics odometry, and sensory interlocks.
"""

import unittest
from pi5_vm_simulator import RaspberryPi5HardwareVM, VirtualPin, VirtualSPIBus
from core.eye_animator import Emotion

class TestRaspberryPi5VM(unittest.TestCase):
    """Test suite for the Raspberry Pi 5 Virtual Machine layer."""

    def setUp(self):
        self.vm = RaspberryPi5HardwareVM()

    def test_pi5_hardware_specifications(self):
        """Verifies Raspberry Pi 5 architecture metadata."""
        self.assertEqual(self.vm.model, "Raspberry Pi 5 Model B Rev 1.0")
        self.assertIn("BCM2712", self.vm.cpu)
        self.assertIn("RP1", self.vm.southbridge)

    def test_rp1_gpio_pin_registration(self):
        """Verifies all Project Alpha hardware pins are registered in the RP1 matrix."""
        required_pins = [25, 5, 6, 12, 13, 16, 17, 27, 4, 26, 22, 23, 24, 8, 7]
        for pin in required_pins:
            self.assertIn(pin, self.vm.pins, f"Pin {pin} must be registered in RP1 matrix")

    def test_virtual_spi_transfer_recording(self):
        """Verifies SPI0 transfers record commands and data across CE0 and CE1."""
        spi = self.vm.spi_bus
        # Send LCD RAMWR command (0x2C) to CE0 (Left Eye)
        spi.record_transfer(device_id=0, is_cmd=True, payload=[0x2C])
        # Send 1024 bytes of pixel data
        spi.record_transfer(device_id=0, is_cmd=False, payload=[0x00] * 1024)

        self.assertEqual(spi.frames_rendered[0], 1)
        self.assertEqual(spi.data_bytes_sent[0], 1024)

    def test_kinematics_odometry(self):
        """Verifies forward drive translates to planar displacement."""
        # Drive forward at 50% PWM (Pins 6 and 13)
        self.vm.pins[6].set_value(0.5, freq=1000)
        self.vm.pins[13].set_value(0.5, freq=1000)
        self.vm.pins[12].set_value(0.0)
        self.vm.pins[16].set_value(0.0)

        initial_x = self.vm.sim_x_cm
        self.vm.update_kinematics(dt=1.0)
        # Should have moved forward by ~10 cm (0.5 * 20 cm/s * 1s)
        self.assertGreater(self.vm.sim_x_cm, initial_x)

    def test_cliff_hazard_injection(self):
        """Verifies cliff drop sensor injection logic."""
        # Safe state (reflection received -> is_active = True)
        self.vm.trigger_cliff(left_cliff=False, right_cliff=False)
        self.assertTrue(self.vm.pins[17].is_active)
        self.assertTrue(self.vm.pins[27].is_active)

        # Cliff drop on left side (reflection lost -> is_active = False)
        self.vm.trigger_cliff(left_cliff=True, right_cliff=False)
        self.assertFalse(self.vm.pins[17].is_active)
        self.assertTrue(self.vm.pins[27].is_active)

    def test_head_touch_injection(self):
        """Verifies capacitive head touch sensor toggling."""
        self.vm.trigger_head_touch(False)
        self.assertFalse(self.vm.pins[4].is_active)

        self.vm.trigger_head_touch(True)
        self.assertTrue(self.vm.pins[4].is_active)

if __name__ == "__main__":
    unittest.main()
