@echo off
REM =============================================================================
REM Project Alpha: Quick Interactive Launcher (Windows Command Prompt / Explorer)
REM =============================================================================

cd /d "%~dp0"
cls
echo ==========================================================
echo     PROJECT ALPHA - RASPBERRY PI 5 VIRTUAL MACHINE
echo ==========================================================
echo   1) Run Pi 5 Autonomous Work Simulation (7 Phases)
echo   2) Interactive Terminal Chat with Alpha (Voice ^& Memory)
echo   3) Launch Web Digital Twin Simulator (http://localhost:8085)
echo   4) Export Dual-Eye 16 Expression Preview Snapshots
echo   5) Run Unit Test Suite (25 Tests)
echo ==========================================================
set /p choice="Select option [1-5] (default: 1): "
if "%choice%"=="" set choice=1

REM Check if python is available
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo [!] Python was not found in Windows PATH.
    echo Trying WSL...
    wsl bash run.sh
    pause
    exit /b
)

if "%choice%"=="1" (
    python pi5_vm_simulator.py
) else if "%choice%"=="2" (
    python pi5_vm_simulator.py --interactive
) else if "%choice%"=="3" (
    start http://localhost:8085
    python pi5_vm_simulator.py --web
) else if "%choice%"=="4" (
    python main.py --preview-eyes
) else if "%choice%"=="5" (
    python -m unittest discover tests/
) else (
    echo Invalid choice.
)

pause
