# ROS 2 Teleoperated Robot using ESP32

A teleoperated differential drive robot built with ROS 2 Jazzy and ESP32.
Controlled via arrow keys over WiFi with live camera feedback.

## Features
- Arrow key teleoperation via ROS 2
- Variable speed control (8 levels)
- Path recording and autonomous retracing
- Live FPV camera feed via smartphone
- Runs on WSL2 Ubuntu 24.04

## System Architecture
Keyboard → arrow_teleop → /cmd_vel → esp32_bridge → ESP32 → Motors
Phone Camera → camera_publisher → /camera/image_raw → rqt_image_view

## Hardware
- ESP32 Dev Module
- L298N Motor Driver
- 2x DC Motors + Caster Wheel
- 12V Battery + Buck Converter (12V → 5V)
- Smartphone (IP Webcam for FPV)

## Software Stack
- ROS 2 Jazzy on WSL2 Ubuntu 24.04
- Arduino IDE for ESP32 firmware
- OpenCV + cv_bridge for camera
- Python 3.12

## Quick Start

### 1. Flash ESP32
Open `esp32_firmware/robot_esp32.ino` in Arduino IDE and flash.

### 2. Build ROS Package
```bash
cd ros2_ws
colcon build --packages-select esp32_robot
source install/setup.bash
```

### 3. Connect to ESP_ROBOT WiFi hotspot

### 4. Run
```bash
# Terminal 1
ros2 run esp32_robot esp32_bridge

# Terminal 2
ros2 run esp32_robot arrow_teleop

# Terminal 3 (optional - camera)
ros2 run esp32_robot camera_publisher
ros2 run rqt_image_view rqt_image_view
```

## Controls
| Key | Action |
|-----|--------|
| ↑ | Forward |
| ↓ | Backward |
| ← | Turn Left |
| → | Turn Right |
| Space | Stop |
| r | Retrace path |
| + / - | Speed up / down |

## Packet Protocol
ESP32 receives: `lin,ang,speed,flag\n`
