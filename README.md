# Fume Hood Sash Automation

This project provides a robust, API-driven system to automate a fume hood sash. It is designed to run on a Raspberry Pi as a set of managed services.

## Project Structure

The project is organized into two main components within the `src/hood_sash_automation` directory:

-   **`actuator/`**: Contains the complete logic for controlling the motorized fume hood sash. It uses multiple Hall effect sensors for precise positioning, a relay for motor control, a current sensor for collision detection, an LCD for status display, and physical buttons for manual control. It exposes an HTTP API for remote commands.
-   **`sensor/`**: Contains the logic for a simple, single-point sash position sensor. It exposes an HTTP API to report the current status.

## Installation

This package is designed to be installed on a Raspberry Pi from a clone of this repository.

### Prerequisites

-   Python 3.7+
-   Ensure I2C is enabled on your Raspberry Pi (`sudo raspi-config`).

### Setup
1.  Clone the repository to your Raspberry Pi:
    ```bash
    git clone https://github.com/AccelerationConsortium/fume-hood-sash-automation.git
    cd fume-hood-sash-automation
    ```

2.  Create a Python virtual environment and activate it. This isolates the project's dependencies.
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  Install the project and its dependencies. This command installs the package in "editable" mode, which creates executable scripts in your virtual environment's `bin/` directory. The `[actuator,sensor]` part installs the optional dependencies for both components.
    ```bash
    pip install --upgrade pip
    pip install -e ".[actuator,sensor]"
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

All hardware and application settings are managed via YAML files in `src/hood_sash_automation/config`. Before running the services, you should review and customize `src/hood_sash_automation/config/actuator_config.yaml` and `src/hood_sash_automation/config/sensor_config.yaml` to match your specific hardware setup (e.g., GPIO pin numbers, I2C addresses). The files are heavily commented to explain each setting. If you need to use a config outside the package, set `HOOD_SASH_ACTUATOR_CONFIG` or `HOOD_SASH_SENSOR_CONFIG` to the desired YAML path.

## Development Environment Setup

### On a Raspberry Pi (for Deployment)
These instructions are for setting up the application on the target hardware.

1.  **Install Raspberry Pi hardware libraries**:
    Install GPIO support from Raspberry Pi OS instead of PyPI. The PyPI `RPi.GPIO`
    wheel can fail GPIO edge detection on newer Pi/Python combinations.
    ```bash
    sudo apt update
    sudo apt install -y python3-rpi.gpio i2c-tools
    ```

2.  **Clone the repository**:
    ```bash
    cd ~
    git clone https://github.com/AccelerationConsortium/fume-hood-sash-automation.git
    cd fume-hood-sash-automation
    ```

3.  **Create and activate the project virtual environment**:
    Create the venv inside the repo and include system site packages so Python can
    use the OS-provided GPIO package.
    ```bash
    python3 -m venv venv --system-site-packages
    source venv/bin/activate
    ```

4.  **Install Python dependencies for this Pi**:
    On an actuator Pi, install only the actuator extra. On a sensor Pi, install
    only the sensor extra.
    ```bash
    pip install --upgrade pip
    pip install -e ".[actuator]"
    ```
    For a sensor-only Pi:
    ```bash
    pip install -e ".[sensor]"
    ```

5.  **Confirm safe startup settings**:
    Keep startup homing disabled while commissioning. If `home_on_startup` is set
    to `true`, the actuator may move immediately when the API service starts or
    the Pi reboots.
    ```yaml
    home_on_startup: false
    bounce_ms: 200
    ```

### On macOS / Windows / Linux (for Local Development & Testing)
These instructions use mock libraries to allow for development and testing on a machine without Raspberry Pi hardware.

1.  **Clone the repository and create the virtual environment**:
    (Same as above)

2.  **Install dependencies with mock libraries**:
    First, install the `fake-rpigpio` mock library.
    ```bash
    pip install fake-rpigpio
    ```
    Next, install the project with the testing and actuator extras. `smbus2` (required by actuator) is a pure Python library and will install correctly on your Mac.
    ```bash
    pip install -e ".[actuator,sensor,test]"
    ```

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

### Starting the API Service

**IMPORTANT**: The API service must be running for remote control to work.

#### Option 1: Direct Command (Development/Testing)
```bash
# Make sure you're in the project directory and virtual environment is activated
cd ~/fume-hood-sash-automation
source venv/bin/activate

# Start the actuator API service (runs on port 5000)
hood_sash_automation_actuator

# On a sensor Pi, start the sensor API service (runs on port 5005)
hood_sash_automation_sensor
```

#### Option 2: Using Systemd (Production)
```bash
# Start services
sudo systemctl start actuator.service
sudo systemctl start sensor.service

# Check that services are running
sudo systemctl status actuator.service
sudo systemctl status sensor.service
```

### Using the API

Once the API service is running, you can control it via HTTP requests:

For the full endpoint reference and dashboard integration notes, see the
[API Guide](src/hood_sash_automation/api/API.md).

#### Actuator API (Port 5000)

Set a base URL for the Pi. Use the Wi-Fi/LAN IP or Tailscale IP:
```bash
PI=http://100.64.254.100:5000
```

**Health check:**
```bash
curl "$PI/health"
```
Example response:
```json
{
  "status": "healthy",
  "actuator": {
    "current_position": 3,
    "is_moving": false
  }
}
```

**Move to a position:**
```bash
curl -X POST "$PI/move" \
  -H "Content-Type: application/json" \
  -d '{"position": 3}'
```
Example response:
```json
{
  "message": "Moving to position 3"
}
```

**Stop movement:**
```bash
curl -X POST "$PI/stop"
```

**Get current status:**
```bash
curl "$PI/status"
```
Example response:
```json
{
  "current_position": 3,
  "is_moving": false
}
```

**Get current position only:**
```bash
curl "$PI/position"
```
Example response:
```json
{
  "position": 3
}
```
If no Hall sensor is active, `position` is `null`.

**Monitor movement:**
```bash
while true; do
  curl -s "$PI/status"
  echo
  sleep 0.5
done
```

#### Sensor API (Port 5005)

Set a base URL for the sensor Pi:
```bash
SENSOR_PI=http://100.64.254.101:5005
```

**Get sensor status:**
```bash
curl "$SENSOR_PI/status"
```
Example response:
```json
{
  "magnet_present": true
}
```

### Managing the Services (Systemd)
- **Check Status**:
  ```bash
  sudo systemctl status actuator.service
  sudo systemctl status sensor.service
  ```
- **View Logs**: All output is handled by `journald`. To see the logs:
  ```bash
  sudo journalctl -u actuator.service -f
  ```
  *(The `-f` flag follows the log in real-time).*
- **Stop/Start/Restart**:
  ```bash
  sudo systemctl stop actuator.service
  sudo systemctl start actuator.service
  sudo systemctl restart actuator.service
  ```

## Remote Control Example
The `examples/` directory contains `remote_control_example.py`, which demonstrates how to control the sash from any computer on the same network.

### Prerequisites
**The API service must be running on your Raspberry Pi first** (see [Starting the API Service](#starting-the-api-service) above).

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
API Response: Moving to position 1
  [Polling] Current Position: 1, Is Moving: false
Movement finished. Final position: 1

>>> Sending command to move to position 2...
API Response: Moving to position 2
  [Polling] Current Position: 1, Is Moving: true
  [Polling] Current Position: 2, Is Moving: false
Movement finished. Final position: 2

Sequence complete.
```

## Testing

This project uses a comprehensive three-layer testing approach for safe development and deployment.

### Quick Start Testing

#### Development Testing (on your laptop)
```bash
# Development testing (local laptop)
./tests/docker-test/scripts/test_local.sh integration

# If integration passes, run full tests
./tests/docker-test/scripts/test_local.sh all
```

#### Pi Testing (on deployed Raspberry Pi)
```bash
# Deploy to Pi
git push && ssh sdl2@your-pi-ip "cd ~/fume-hood-sash-automation && git pull"

# Pi actuator hardware access smoke test
ssh sdl2@your-pi-ip "cd ~/fume-hood-sash-automation && source venv/bin/activate && python tests/device-test/smoke_tests.py --component actuator"

# Running actuator API service test
ssh sdl2@your-pi-ip "cd ~/fume-hood-sash-automation && source venv/bin/activate && python tests/device-test/api_service_test.py --service actuator"
```

#### Hardware Integration
```bash
# Only after Pi testing passes - start services with real hardware
ssh sdl2@your-pi-ip "sudo systemctl start actuator.service"
```

### Testing Strategy

| Test Layer | Where | Duration | Coverage | Safety |
|------------|-------|----------|----------|---------|
| Docker Tests | Local laptop | 5-30s | Business logic, mocked hardware | Completely safe |
| Pi Device Tests | Raspberry Pi | 30-60s | ARM compatibility, GPIO/I2C access | Safe when relays are stopped |
| Hardware Tests | Pi + devices | Manual | Full integration | Requires connected hardware and supervision |

### Pi Testing Without Hardware Movement

Pi smoke tests validate the environment and safe hardware access before movement tests:

- Code compatibility on ARM/Pi OS
- GPIO and I2C access
- Python module imports
- Configuration loading
- Safe relay setup and Hall sensor reads

```bash
cd ~/fume-hood-sash-automation
source venv/bin/activate
sudo systemctl stop actuator.service
python tests/device-test/smoke_tests.py --component actuator
sudo systemctl start actuator.service
```

Expected successful summary:
```text
Actuator tests: 5/5 passed
```

### Detailed Testing Documentation

#### Docker Testing
- [Docker Testing Guide](tests/docker-test/Docker_Test.md) - local development testing with mocked hardware.
- Fast iteration and development testing.
- Completely safe for development environments.
- Covers business logic and API endpoints.

#### Device Testing
- [Device Testing Guide](tests/device-test/Device_Test.md) - Raspberry Pi smoke and API testing.
- Real Pi hardware validation.
- GPIO/I2C access verification.
- ARM/Pi OS compatibility testing.

#### Hardware Integration Testing
- [Pi Hardware Setup](tests/device-test/Device_Test.md#pi-zero-2w-specific-setup) - interface configuration and optimization.
- Full system integration with connected devices.
- Real sensor and actuator testing.
- Production deployment validation.

### Test Structure

```text
tests/
|-- docker-test/              # Local Docker testing
|   |-- Docker_Test.md        # Docker testing guide
|   |-- scripts/              # Testing scripts
|   `-- tests/                # Mocked logic tests
`-- device-test/              # Pi device testing
    |-- Device_Test.md        # Device testing guide
    |-- smoke_tests.py        # Pi hardware access smoke test
    `-- api_service_test.py   # Running API service test
```

### Testing Best Practices

1. Start with Docker tests for fast logic feedback when changing code.
2. Run Pi smoke tests before movement tests.
3. Keep `home_on_startup: false` while commissioning.
4. Only connect or move hardware after Pi tests pass.
5. Keep a physical stop or power cutoff ready during movement tests.

### Troubleshooting

#### Docker Tests
- Permission errors: check Docker Desktop is running.
- Import errors: rebuild the container with `./tests/docker-test/scripts/setup_local_only.sh`.

#### Pi Device Tests
- GPIO/I2C access: ensure the user is in `gpio` and `i2c` groups.
- Module not found: activate `venv` and run `pip install -e ".[actuator]"`.
- GPIO channel already in use: stop `actuator.service` before smoke tests.

#### Hardware Integration
- Device not responding: check physical connections and power.
- Current sensor errors: verify I2C address and wiring with `sudo i2cdetect -y 1`.
- Motor not moving: check relay connections, actuator power, and limit switches.
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
