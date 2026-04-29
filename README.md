# Fume Hood Sash Automation

This project provides a robust, API-driven system to automate a fume hood sash. It is designed to run on a Raspberry Pi as a set of managed services.

## Project Structure

The project is organized into two main components within the `src/hood_sash_automation` directory:

-   **`actuator/`**: Contains the complete logic for controlling the motorized fume hood sash. It uses multiple Hall effect sensors for precise positioning, a relay for motor control, a current sensor for collision detection, an LCD for status display, and physical buttons for manual control. It exposes an HTTP API for remote commands.
-   **`sensor/`**: Contains the logic for a simple, single-point sash position sensor. It exposes an HTTP API to report the current status.

## Installation

This package is designed to be installed on a Raspberry Pi from a clone of this repository.

### Prerequisites

- Python 3.7+
- I2C enabled on the Raspberry Pi (`sudo raspi-config`)
- GPIO and I2C tools installed from Raspberry Pi OS:
  ```bash
  sudo apt update
  sudo apt install -y python3-rpi.gpio i2c-tools
  ```

### Setup
1.  Clone the repository to your Raspberry Pi:
    ```bash
    git clone https://github.com/AccelerationConsortium/fume-hood-sash-automation.git
    cd fume-hood-sash-automation
    ```

2.  Create a Python virtual environment and activate it. Use system site packages so the venv can use the OS-provided GPIO library.
    ```bash
    python3 -m venv venv --system-site-packages
    source venv/bin/activate
    ```

3.  Install the project and its dependencies. On an actuator Pi, install the actuator extra. On a sensor Pi, install the sensor extra.
    ```bash
    pip install --upgrade pip
    pip install -e ".[actuator]"
    # or, for a sensor-only Pi:
    pip install -e ".[sensor]"
    ```

## Quick Start

After installation, here's how to get the API service running:

1. **Start the API service:**
   ```bash
   # Make sure you're in the project directory with venv activated
   hood_sash_automation_actuator
   ```

2. **Test the API** (in another terminal):
   ```bash
   # Check if the service is running
   curl http://localhost:5000/status

   # Move to position 2
   curl -X POST http://localhost:5000/move -H "Content-Type: application/json" -d '{"position": 2}'
   ```

3. **Use the remote control example:**
   ```bash
   python examples/remote_control_example.py
   ```

## Configuration

- Config files live in `src/hood_sash_automation/config`.
- Use `actuator_config.yaml` for the actuator Pi and `sensor_config.yaml` for the sensor Pi.
- Review GPIO pins, I2C addresses, movement timeouts, and safety thresholds before deployment.
- Keep `home_on_startup: false` while commissioning so the sash does not move when the service starts.
- To use a config outside the package, set `HOOD_SASH_ACTUATOR_CONFIG` or `HOOD_SASH_SENSOR_CONFIG` to the YAML file path.

## Deployment (Systemd Services)

For the services to run automatically on boot, they should be managed by `systemd`.

### 1. Configure Service Files
The service files in the `systemd/` directory are templates. You must edit them to set the correct `User` and ensure the `WorkingDirectory` points to the absolute path of your project directory on the Pi. The services load their default config files from `src/hood_sash_automation/config`.

### 2. Install the Services
Copy the configured service files to the `systemd` directory and set the correct permissions:
```bash
sudo cp systemd/*.service /etc/systemd/system/
sudo chmod 644 /etc/systemd/system/actuator.service
sudo chmod 644 /etc/systemd/system/sensor.service
```

### 3. Enable and Start the Services
Reload the `systemd` daemon to recognize the new files, then enable the services to start on boot:
```bash
sudo systemctl daemon-reload
sudo systemctl enable actuator.service
sudo systemctl enable sensor.service
```
You can now either reboot your Pi or start the services manually:
```bash
sudo systemctl start actuator.service
sudo systemctl start sensor.service
```

Verify the actuator service is enabled, running, and serving the API:
```bash
systemctl is-enabled actuator.service
sudo systemctl status actuator.service
curl http://localhost:5000/status
```

After a reboot, run the same checks. From a Tailscale-connected machine, use the
Pi's Tailscale IP:
```bash
curl http://<pi-tailscale-ip>:5000/status
```

## Usage

Run the services through `systemd` for normal deployment:

```bash
sudo systemctl start actuator.service
sudo systemctl start sensor.service
sudo systemctl status actuator.service
sudo systemctl status sensor.service
```

Use the Pi's Wi-Fi/LAN IP or Tailscale IP to call the APIs:

- Actuator service: `http://<actuator-pi-ip>:5000`
- Sensor service: `http://<sensor-pi-ip>:5005`
- Full endpoint reference: [API Guide](src/hood_sash_automation/api/API.md)

Quick actuator health check:

```bash
curl http://<actuator-pi-ip>:5000/health
```

## Remote Control Example
The `examples/` directory contains `remote_control_example.py`, which demonstrates how to control the sash from any computer on the same network.

### Prerequisites
**The API service must be running on your Raspberry Pi first** (see [Usage](#usage) above).

### Usage
1.  **Install Dependencies**: The script requires the `requests` library.
    ```bash
    pip install requests
    ```
2.  **Configure Host**: Open `examples/remote_control_example.py` and change the `PI_HOST` variable to the Wi-Fi/LAN IP or Tailscale IP of your Raspberry Pi.
3.  **Run the Script**:
    ```bash
    python examples/remote_control_example.py
    ```

### What It Does
The script will:
- Check if the API service is running
- Move the sash to home position (1)
- Cycle through all positions (2, 3, 4, 5)
- Return to home position
- Display real-time status updates

### Example Output
```
Successfully connected to the actuator service at http://100.x.y.z:5000

>>> Sending command to move to position 1...
API Response: Moving sash to position 1
  [Polling] Current Position: 1, Is Moving: false
Movement finished. Final position: 1

>>> Sending command to move to position 2...
API Response: Moving sash to position 2
  [Polling] Current Position: 1, Is Moving: true
  [Polling] Current Position: 2, Is Moving: false
Movement finished. Final position: 2

Sequence complete.
```

## Testing

Use Docker tests for local logic checks and device tests on the Raspberry Pi before moving hardware.

- Docker testing guide: [tests/docker-test/Docker_Test.md](tests/docker-test/Docker_Test.md)
- Device testing guide: [tests/device-test/Device_Test.md](tests/device-test/Device_Test.md)

Common commands:
```bash
# Local mocked tests
./tests/docker-test/scripts/setup_local_only.sh
./tests/docker-test/scripts/test_local.sh integration

# Pi smoke/API tests
cd ~/fume-hood-sash-automation
source venv/bin/activate
sudo systemctl stop actuator.service
python tests/device-test/smoke_tests.py --component actuator
sudo systemctl start actuator.service
python tests/device-test/api_service_test.py --service actuator
```

## Hardware
- Raspberry Pi (Zero 2W, 3B+, 4, etc.)
- Digital Hall Effect Sensors
- DC Motor Linear Actuator (for actuator)
- 2-Channel Relay Board (for actuator)
- INA219 Current Sensor (for actuator)
- DFR0997 LCD Display (for actuator, optional)
- Physical Push Buttons (for actuator, optional)

## Notes
- GPIO pin numbers use the BCM numbering scheme.
- The `actuator` and `sensor` components are generally designed for separate devices but can be run on the same Raspberry Pi if needed.
