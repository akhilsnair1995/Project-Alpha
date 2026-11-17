#!/usr/bin/env bash
# =============================================================================
# Project Alpha: QEMU ARM64 Virtual Machine Launcher for Raspberry Pi 5
# Launches a 64-bit ARM Cortex-A76 VM matching Raspberry Pi 5 architecture
# =============================================================================

set -e

VM_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE_NAME="raspios_arm64_bookworm.qcow2"
IMAGE_PATH="${VM_DIR}/${IMAGE_NAME}"
MEMORY="4096"
CPUS="4"
PORT_HTTP="8085"
PORT_SSH="2222"

echo "================================================================="
echo "  PROJECT ALPHA: RASPBERRY PI 5 QEMU VIRTUAL MACHINE"
echo "================================================================="
echo "Target Architecture: aarch64 (ARMv8.2-A / Cortex-A76)"
echo "Memory:              ${MEMORY} MB"
echo "vCPUs:               ${CPUS}"
echo "Port Forwarding:     Host ${PORT_HTTP} -> Guest 8085 (Digital Twin)"
echo "                     Host ${PORT_SSH}  -> Guest 22   (SSH)"
echo "================================================================="

# Check for QEMU system binary
if ! command -v qemu-system-aarch64 &> /dev/null; then
    echo "[!] qemu-system-aarch64 is not installed."
    echo "    To install on Debian/Ubuntu/WSL:"
    echo "      sudo apt update && sudo apt install -y qemu-system-arm qemu-efi-aarch64 cloud-image-utils"
    echo ""
    echo "    Alternatively, use the lightweight Python Hardware VM simulator:"
    echo "      python3 pi5_vm_simulator.py"
    exit 1
fi

# Prepare empty virtual disk if none exists
if [ ! -f "${IMAGE_PATH}" ]; then
    echo "[*] Creating 16GB sparse qcow2 disk image at: ${IMAGE_PATH}"
    qemu-img create -f qcow2 "${IMAGE_PATH}" 16G
fi

echo "[*] Starting Raspberry Pi 5 virtual machine instance..."

qemu-system-aarch64 \
    -M virt \
    -cpu cortex-a76 \
    -smp "${CPUS}" \
    -m "${MEMORY}" \
    -device virtio-gpu-pci \
    -device virtio-net-pci,netdev=net0 \
    -netdev user,id=net0,hostfwd=tcp::${PORT_SSH}-:22,hostfwd=tcp::${PORT_HTTP}-:8085 \
    -drive file="${IMAGE_PATH}",if=virtio,format=qcow2 \
    -nographic
