#!/usr/bin/env bash
# =============================================================================
# Project Alpha: Quick Interactive Launcher (Linux / WSL)
# =============================================================================

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

if [ -f "$DIR/.venv/bin/activate" ]; then
    source "$DIR/.venv/bin/activate"
fi

echo "=========================================================="
echo "    PROJECT ALPHA - RASPBERRY PI 5 VIRTUAL MACHINE"
echo "=========================================================="
echo "  1) Run Pi 5 Autonomous Work Simulation (7 Phases)"
echo "  2) Interactive Terminal Chat with Alpha (Voice & Memory)"
echo "  3) Launch Web Digital Twin Simulator (http://localhost:8085)"
echo "  4) Export Dual-Eye 16 Expression Preview Snapshots"
echo "  5) Run Unit Test Suite (25 Tests)"
echo "=========================================================="
read -p "Select option [1-5] (default: 1): " choice
choice=${choice:-1}

case "$choice" in
    1)
        python3 pi5_vm_simulator.py
        ;;
    2)
        python3 pi5_vm_simulator.py --interactive
        ;;
    3)
        echo "[*] Starting server and opening http://localhost:8085 ..."
        (explorer.exe "http://localhost:8085" 2>/dev/null || xdg-open "http://localhost:8085" 2>/dev/null || true) &
        python3 pi5_vm_simulator.py --web
        ;;
    4)
        python3 main.py --preview-eyes
        ;;
    5)
        python3 -m unittest discover tests/
        ;;
    *)
        echo "Invalid option. Exiting."
        ;;
esac
