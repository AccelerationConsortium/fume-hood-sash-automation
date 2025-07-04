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
    git clone https://github.com/your-username/fume-hood-sash-automation.git
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
   python users/examples/remote_control_example.py
   ```

## Configuration

All hardware and application settings are managed via YAML files in the `/users/config` directory. Before running the services, you should review and customize `users/config/actuator_config.yaml` and `users/config/sensor_config.yaml` to match your specific hardware setup (e.g., GPIO pin numbers, I2C addresses). The files are heavily commented to explain each setting.

## Development Environment Setup

### On a Raspberry Pi (for Deployment)
These instructions are for setting up the application on the target hardware.

1.  **Create the Python environment in ~/Projects**:
    ```bash
    # Create Projects directory if it doesn't exist
    mkdir -p ~/Projects
    cd ~/Projects
    
    # Create virtual environment with system site packages
    python3 -m venv sash_env --system-site-packages
    
    # Activate the environment
    source sash_env/bin/activate
    ```

2.  **Set up auto-activation on SSH login**:
    ```bash
    # Edit your profile to auto-activate the environment
    nano ~/.profile
    
    # Add this line to the end of ~/.profile:
    source ~/Projects/sash_env/bin/activate
    
    # Apply the changes
    source ~/.profile
    ```

3.  **Clone the repository**:
    ```bash
    # Make sure you're in the Projects directory with environment activated
    cd ~/Projects
    git clone https://github.com/your-username/fume-hood-sash-automation.git
    cd fume-hood-sash-automation
    ```

4.  **Install all dependencies**:
    This command installs the base package along with the extras needed for the actuator, sensor, and the real Raspberry Pi hardware libraries.
    ```bash
    pip install --upgrade pip
    pip install -e ".[actuator,sensor,rpi_hardware]"
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
The service files in the `systemd/` directory are templates. You must edit them to set the correct `User` and ensure the `WorkingDirectory` points to the absolute path of your project directory on the Pi. The scripts will automatically find the config files in the `users/config/` subdirectory.

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

## Usage

### Starting the API Service

**🚨 IMPORTANT**: The API service must be running for remote control to work.

#### Option 1: Direct Command (Development/Testing)
```bash
# Make sure you're in the project directory and virtual environment is activated
cd fume-hood-sash-automation
source venv/bin/activate

# Start the actuator API service (runs on port 5000)
hood_sash_automation_actuator

# In another terminal, start the sensor API service (runs on port 5005)
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

#### Actuator API (Port 5000)

**Move to a position:**
```bash
curl -X POST http://raspberrypi.local:5000/move \
  -H "Content-Type: application/json" \
  -d '{"position": 3}'
```

**Stop movement:**
```bash
curl -X POST http://raspberrypi.local:5000/stop
```

**Get current status:**
```bash
curl http://raspberrypi.local:5000/status
```
Example response:
```json
{
  "current_position": 3,
  "is_moving": false,
  "last_movement": "2024-01-15T10:30:00Z"
}
```

**Get current position only:**
```bash
curl http://raspberrypi.local:5000/position
```

#### Sensor API (Port 5005)

**Get sensor status:**
```bash
curl http://raspberrypi.local:5005/status
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
The `users/examples/` directory contains an example script, `remote_control_example.py`, that demonstrates how to control the sash from any computer on the same network.

### Prerequisites
**⚠️ The API service must be running on your Raspberry Pi first** (see [Starting the API Service](#starting-the-api-service) above).

### Usage
1.  **Install Dependencies**: The script requires the `requests` library.
    ```bash
    pip install requests
    ```
2.  **Configure Host**: Open `users/examples/remote_control_example.py` and change the `PI_HOST` variable to the IP address or hostname of your Raspberry Pi.
3.  **Run the Script**:
    ```bash
    python users/examples/remote_control_example.py
    ```

### What It Does
The script will:
- ✅ Check if the API service is running
- 🏠 Move the sash to home position (1)
- 🔄 Cycle through all positions (2, 3, 4, 5)
- 🏠 Return to home position
- 📊 Display real-time status updates

### Example Output
```
Successfully connected to the actuator service at http://raspberrypi.local:5000

>>> Sending command to move to position 1...
API Response: Moving to position 1
  [Polling] Current Position: 1, Is Moving: false
Movement finished. Final position: 1

>>> Sending command to move to position 2...
API Response: Moving to position 2
  [Polling] Current Position: 1, Is Moving: true
  [Polling] Current Position: 2, Is Moving: false
Movement finished. Final position: 2

✅ Sequence complete.
```

## Testing

This project uses a comprehensive three-layer testing approach for safe development and deployment.

**📋 See [tests/Test.md](tests/Test.md) for complete testing documentation.**

### Quick Start
```bash
# Development testing (local laptop)
./tests/docker-test/scripts/test_local.sh integration

# Pi device testing (safe without hardware)
python tests/device-test/smoke_tests.py

# Hardware integration (with connected devices)
sudo systemctl start actuator sensor
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