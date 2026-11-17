# Raspberry Pi 5 Virtual Machine & Simulation Suite

This directory provides environments and deployment scripts to run Project Alpha's firmware in a virtualized Raspberry Pi 5 platform before flashing to physical hardware.

---

## 3 Ways to Run Project Alpha in a Virtualized Environment

| Environment | Best For | Prerequisites | Command |
| :--- | :--- | :--- | :--- |
| **1. Python Hardware VM (`pi5_vm_simulator.py`)** | Instant testing, full RP1 GPIO & SPI bus emulation, work simulation | None (pure Python standard library) | `python3 pi5_vm_simulator.py` |
| **2. Docker Pi 5 Container VM** | Containerized deployment, isolation, continuous integration | Docker & Docker Compose | `docker compose -f vm/docker-compose.yml up` |
| **3. Full QEMU ARM64 Cortex-A76 VM** | Full OS emulation, testing Raspberry Pi OS 64-bit kernel & systemd | QEMU (`qemu-system-aarch64`) | `bash vm/setup_qemu_pi5.sh` |

---

## Architecture of the Raspberry Pi 5 Virtual Machine

Raspberry Pi 5 introduces the custom **RP1 Southbridge chip** for all 40-pin GPIO, PWM, SPI, and I2C operations.

```
       ┌────────────────────────────────────────────────────────┐
       │             Raspberry Pi 5 Virtual Machine             │
       │     Debian 12 Bookworm 64-bit (ARMv8.2-A Cortex-A76)    │
       └───────────────────────────┬────────────────────────────┘
                                   │
               ┌───────────────────┴───────────────────┐
               ▼                                       ▼
  ┌─────────────────────────┐             ┌─────────────────────────┐
  │   RP1 I/O SOUTHBRIDGE   │             │   PERIPHERAL BUSES      │
  │ • GPIO 25: MG90S Pan    │             │ • SPI0: 2x GC9A01 LCDs  │
  │ • GPIO 05: MG90S Tilt   │             │   (CE0=Left, CE1=Right) │
  │ • GPIO 6/12/13/16 Motors│             │ • I2S Bus: PCM Audio    │
  │ • GPIO 17/27: Cliff IR  │             │ • I2C Bus: ToF & ADC    │
  │ • GPIO 4: Capacitive    │             │ • V4L2: Vision Camera   │
  └─────────────────────────┘             └─────────────────────────┘
```
