#!/usr/bin/env bash
# =============================================================================
# Project Alpha: Raspberry Pi 5 (8 GB) Provisioning Script
# Target OS: Ubuntu 24.04 LTS Server (64-bit) + ROS 2 Jazzy Jalisco (ros-jazzy-ros-base)
# =============================================================================

set -e

echo "==================================================================="
echo "  PROJECT ALPHA: PI 5 PROVISIONING (UBUNTU 24.04 + ROS 2 JAZZY)   "
echo "==================================================================="

if [ "$EUID" -ne 0 ]; then
  echo "[!] Please run as root (sudo bash setup_pi5_ros2.sh)"
  exit 1
fi

REAL_USER="${SUDO_USER:-$USER}"
USER_HOME=$(eval echo "~$REAL_USER")

# 1. System Update & Essential Build Dependencies
echo "[1/6] Updating system packages..."
apt-get update && apt-get upgrade -y
apt-get install -y \
  software-properties-common \
  curl \
  gnupg \
  lsb-release \
  git \
  build-essential \
  cmake \
  python3-pip \
  python3-dev \
  python3-setuptools \
  python3-colcon-common-extensions \
  python3-rosdep \
  python3-vcstool \
  v4l-utils \
  espeak \
  alsa-utils \
  libasound2-dev \
  zram-tools \
  udev

# 2. Configure zram Swap for 8 GB RAM Headroom (Optimal for Local LLMs)
echo "[2/6] Configuring zram swap compression for local LLM inference headroom..."
cat << 'EOF' > /etc/default/zramswap
# Project Alpha zram configuration: 4GB compressed RAM swap
ALGO=zstd
PERCENT=50
PRIORITY=100
EOF
systemctl restart zramswap || true
echo "  ✓ zramswap active. RAM + compressed swap ready."

# 3. Setup ROS 2 Jazzy Jalisco Repositories & Install Base
echo "[3/6] Installing ROS 2 Jazzy Jalisco (ros-jazzy-ros-base)..."
add-apt-repository universe -y

curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(. /etc/os-release && echo $UBUNTU_CODENAME) main" | tee /etc/apt/sources.list.d/ros2.list > /dev/null

apt-get update
apt-get install -y \
  ros-jazzy-ros-base \
  ros-jazzy-geometry-msgs \
  ros-jazzy-std-msgs \
  ros-jazzy-sensor-msgs \
  ros-dev-tools

# Initialize rosdep
if [ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]; then
  rosdep init || true
fi
sudo -u "$REAL_USER" rosdep update || true

# Add ROS 2 setup to bashrc
if ! grep -q "source /opt/ros/jazzy/setup.bash" "$USER_HOME/.bashrc"; then
  echo "source /opt/ros/jazzy/setup.bash" >> "$USER_HOME/.bashrc"
fi

# 4. Configure ESP32-S3 Mini udev Rules
echo "[4/6] Installing udev rules for ESP32-S3 Mini USB serial..."
cat << 'EOF' > /etc/udev/rules.d/99-alpha-esp32.rules
# Espressif ESP32-S3 Native USB CDC & CP210x/CH34x USB-UART bridges
SUBSYSTEM=="tty", ATTRS{idVendor}=="303a", ATTRS{idProduct}=="1001", MODE="0666", SYMLINK+="alpha_esp32"
SUBSYSTEM=="tty", ATTRS{idVendor}=="303a", MODE="0666", SYMLINK+="alpha_esp32"
SUBSYSTEM=="tty", ATTRS{idVendor}=="10c4", ATTRS{idProduct}=="ea60", MODE="0666", SYMLINK+="alpha_esp32"
SUBSYSTEM=="tty", ATTRS{idVendor}=="1a86", ATTRS{idProduct}=="7523", MODE="0666", SYMLINK+="alpha_esp32"
EOF

udevadm control --reload-rules
udevadm trigger

# 5. User Hardware Permissions (Dialout, I2C, SPI, Audio, GPIO)
echo "[5/6] Adding user '$REAL_USER' to hardware groups..."
usermod -aG dialout,audio,video,i2c,spi "$REAL_USER" || true

# 6. Python Dependencies for Cognitive Engine
echo "[6/6] Installing Python robot stack dependencies..."
sudo -u "$REAL_USER" pip3 install --break-system-packages \
  pyserial \
  numpy \
  opencv-python-headless \
  pillow \
  sounddevice \
  gtts \
  requests

echo "==================================================================="
echo "  ✓ PROVISIONING COMPLETE!                                         "
echo "  Next steps:                                                      "
echo "    1. Plug in ESP32-S3 via USB-C -> check: ls -l /dev/alpha_esp32"
echo "    2. cd ros2_ws && colcon build --symlink-install                "
echo "    3. source install/setup.bash                                   "
echo "    4. ros2 launch project_alpha_ros alpha_ros.launch.py           "
echo "==================================================================="
