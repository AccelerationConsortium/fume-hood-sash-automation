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
    
## Configuration

All hardware and application settings are managed via YAML files in the `/config` directory. Before running the services, you should review and customize `config/actuator_config.yaml` and `config/sensor_config.yaml` to match your specific hardware setup (e.g., GPIO pin numbers, I2C addresses). The files are heavily commented to explain each setting.

## Development Environment Setup

### On a Raspberry Pi (for Deployment)
These instructions are for setting up the application on the target hardware.

1.  **Clone the repository and create the virtual environment**:
    ```bash
    git clone https://github.com/your-username/fume-hood-sash-automation.git
    cd fume-hood-sash-automation
    python3 -m venv venv
    source venv/bin/activate
    ```
2.  **Install all dependencies**:
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
The service files in the `systemd/` directory are templates. You must edit them to set the correct `User` and ensure the `WorkingDirectory` points to the absolute path of your project directory on the Pi. The scripts will automatically find the config files in the `config/` subdirectory.

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

### Managing the Services
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

### API Endpoints
Once the services are running, you can control them via their HTTP APIs.

#### Actuator API (Port 5000)
- `POST /move`: Moves the sash to a specified position.
  - **Body**: `{"position": <1-5>}`
- `POST /stop`: Stops any current movement.
- `GET /status`: Returns the current status (e.g., current position, if it's moving).
- `GET /position`: Returns the current position.

#### Sensor API (Port 5005)
- `GET /status`: Returns the sensor's status.
  - **Response**: `{"magnet_present": <true/false>}`

## Remote Control Example
The `samples/` directory contains an example script, `remote_control_example.py`, that demonstrates how to control the sash from any computer on the same network.

### Usage
1.  **Install Dependencies**: The script requires the `requests` library.
    ```bash
    pip install requests
    ```
2.  **Configure Host**: Open `samples/remote_control_example.py` and change the `PI_HOST` variable to the IP address or hostname of your Raspberry Pi.
3.  **Run the Script**:
    ```bash
    python samples/remote_control_example.py
    ```
The script will command the sash to its home position, then cycle through all other positions, and finally return home, printing status updates throughout the process.

## Testing

This project uses a **comprehensive three-layer testing approach**:

1. **Local Docker Testing**: Fast development testing with mocked hardware
2. **Pi Zero 2W Testing**: Safe validation on real Pi hardware **without connected devices**
3. **Hardware Integration**: Full testing with connected sensors and actuators

### 🚀 Quick Start Testing

#### **Development Testing** (on your laptop)
```bash
# Set up local Docker testing (one-time)
./docker-test/scripts/setup_local_only.sh

# Quick integration test (recommended - 5-10s)
./docker-test/scripts/test_local.sh integration

# If integration passes, run full tests (30s)
./docker-test/scripts/test_local.sh all
```

#### **Pi Zero 2W Testing** (safe, no hardware required)
```bash
# Deploy to Pi Zero 2W
git push && ssh pi@your-pi-ip "cd fume-hood && git pull"

# Basic validation (30s - covers 95% of Pi compatibility)
ssh pi@your-pi-ip "cd fume-hood && python device-test/smoke_tests.py"

# Optional: API service testing (60s - if using microservices)
ssh pi@your-pi-ip "cd fume-hood && python device-test/api_service_test.py"
```

#### **Hardware Integration** (with connected devices)
```bash
# Only after Pi testing passes - start services with real hardware
ssh pi@your-pi-ip "sudo systemctl start actuator sensor"
```

### 🎯 Testing Strategy

| Test Layer | Where | Duration | Coverage | Safety |
|------------|-------|----------|----------|---------|
| **Docker Tests** | Local laptop | 5-30s | Business logic, mocked hardware | ✅ Completely safe |
| **Pi Device Tests** | Pi Zero 2W | 30-60s | ARM compatibility, GPIO/I2C access | ✅ Safe without devices |
| **Hardware Tests** | Pi + devices | Manual | Full integration | ⚠️ Requires connected hardware |

### 🔧 Pi Zero 2W Testing Without Hardware

**Perfect for development and validation** - test your code on real Pi hardware before connecting expensive devices:

- **Code Validation**: Verify ARM compatibility and Pi environment
- **Safety First**: No risk of hardware damage from code bugs
- **Fast Feedback**: Quick validation before hardware deployment
- **Environment Check**: Confirm GPIO/I2C access and dependencies

```bash
# SSH into your Pi Zero 2W
ssh pi@your-pi-ip

# Install and test (safe for disconnected hardware)
cd fume-hood-sash-automation
pip install -e .[actuator,sensor]
python device-test/smoke_tests.py
```

Expected output with no devices connected:
```
🎉 All smoke tests PASSED! Device is ready.
Result: 7/7 tests passed
- ✅ GPIO access working
- ✅ I2C access working  
- ✅ All modules import correctly
- ✅ Configuration files valid
- ✅ Hardware classes initialize safely
```

### 📚 Testing Documentation
- **[Docker Testing](docker-test/README.md)** - Local development testing with mocked hardware
- **[Device Testing](device-test/README.md)** - Pi Zero 2W testing without connected devices
- **[Pi Hardware Setup](device-test/README.md#pi-zero-2w-specific-setup)** - Interface configuration and optimization

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