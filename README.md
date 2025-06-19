# Fume Hood Sash Automation

This project provides Python scripts to automate a fume hood sash, with options for a sensor-only or a full actuator setup.

## Installation

This package is designed to be installed on a Raspberry Pi. It should be installed from a clone of the repository.

### Prerequisites

Enable I2C on your Raspberry Pi using `raspi-config`.

### Installation

Clone the repository to your Raspberry Pi and install the package. The same command works for both the sensor and actuator devices.

```bash
git clone https://github.com/your-username/fume-hood-sash-automation.git
cd fume-hood-sash-automation
pip install .
```

## Usage

After installation, you can run the scripts from the command line.

### Actuator
```bash
actuator --help
```
This script will control the fume hood sash based on Hall effect sensor inputs. It can also be controlled via a named pipe at `/tmp/pipe`.

### Sensor
**Simple Sensor:**
```bash
sensor
```
This script reads a single Hall effect sensor and turns an LED on or off.

**Networked Sensor:**
```bash
sensor-networked
```
This script provides a TCP server on port 5005 to get the sensor status remotely.

## 1. Sash Actuator
Located in `sash-actuator/`

- Controls a motorized fume hood sash using 5 Hall effect sensors for position feedback.
- Drives a relay board to move the sash up or down.
- Supports commands via command line and a named pipe (`/tmp/pipe`):
  - `position N` (N=1-5): Move to a specific position.
  - `stop`: Interrupt movement.
  - `get`: Return current position.
  - `check_ready`: Check if the sash is fully open.
- Displays position and status on an LCD display.
- Logs sensor transitions and current draw for safety and diagnostics.

## 2. Sash Sensor Lite
Located in `sash-sensor-lite/`

### main.py
- Simple script for a Pi Zero 2W with one Hall effect sensor and one LED.
- Turns the LED on when a magnet is present (sash up), off when not present (sash down).
- Prints a message to the console whenever the sensor state changes.

### main_networked.py
- Advanced version with network support.
- Runs a TCP server (port 5005) to allow remote clients to:
  - Query the current sensor state (`get` or `status` commands).
  - Receive real-time notifications when the sensor state changes (push model).
- Multiple clients can connect and will be notified immediately of sash position changes.

### sensor_client_example.py
- Example Python client for connecting to `main_networked.py`.
- Can query the sensor state and listen for real-time notifications.

## Hardware
- Raspberry Pi (Zero 2W or similar)
- Digital Hall effect sensor(s)
- Relay board (for actuator)
- LED (for sensor lite)
- LCD display (for actuator, optional)

## Notes
- GPIO pin numbers use BCM numbering.
- The actuator and sensor-lite are designed to be modular and can be used together or separately.
- For networked operation, ensure your Pi has a static IP and is accessible on your network.

---

**Note:**
- `sash-actuator` and `sash-sensor-lite` are designed for separate devices and are not intended to be used together on the same Raspberry Pi. Each device runs its own code and serves a distinct function:
  - `sash-actuator` is for controlling the actuator to open and close the sash.
  - `sash-sensor-lite` is for detecting if the sash is "open" (magnet present) and optionally reporting this state over the network.