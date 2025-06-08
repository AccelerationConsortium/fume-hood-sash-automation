# Fume Hood Sash Automation

This project provides code for automating and monitoring a laboratory fume hood sash using Raspberry Pi devices. It includes two main components:

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

## Usage
- See each folder for the main script to run on your Pi.
- For actuator: run `main.py` and use the command line or `/tmp/pipe` for control.
- For sensor lite: run `main.py` for basic operation, or `main_networked.py` for networked operation.
- Use `sensor_client_example.py` to connect to the sensor lite from another device.

## Notes
- GPIO pin numbers use BCM numbering.
- The actuator and sensor-lite are designed to be modular and can be used together or separately.
- For networked operation, ensure your Pi has a static IP and is accessible on your network.

---

**Note:**
- `sash-actuator` and `sash-sensor-lite` are designed for separate devices and are not intended to be used together on the same Raspberry Pi. Each device runs its own code and serves a distinct function:
  - `sash-actuator` is for controlling the actuator to open and close the sash.
  - `sash-sensor-lite` is for detecting if the sash is "open" (magnet present) and optionally reporting this state over the network.