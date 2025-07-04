# Fume Hood Sash Automation - Microservice Setup Guide

## 🎯 Overview

This project provides a **microservice** for remote control of fume hood sash positioning via SSH. 
It exposes a REST API running locally on a Raspberry Pi that can be accessed securely through SSH tunneling from external applications.

## 🏗️ Architecture

```
┌─────────────────┐    SSH/curl     ┌─────────────────┐    GPIO/I2C    ┌─────────────────┐
│   Your UI App   │ ──────────────► │  Raspberry Pi   │ ──────────────► │  Fume Hood      │
│                 │                 │                 │                 │                 │
│ - Web Interface │                 │ - Flask API     │                 │ - Hall Sensors  │
│ - Lab Workflow  │                 │ - SashActuator  │                 │ - Motor Relays  │
│ - Automation    │                 │ - Hardware Ctrl │                 │ - Current Mon.  │
└─────────────────┘                 └─────────────────┘                 └─────────────────┘
        ▲                                     ▲
        │                                     │
        └─── FumeHoodSashClient ──────────────┘
             (Python Client Library)
```

## 📦 Installation

### On Raspberry Pi (Microservice Host)

1. **Clone and Setup**
   ```bash
   git clone <your-repo-url>
   cd fume-hood-sash-automation
   pip install -e .
   ```

2. **Configure Hardware**
   Edit `users/config/actuator_config.yaml`:
   ```yaml
   hall_pins: [5, 6, 13, 19, 26]     # Position sensors
   relay_ext_pin: 27                  # Extend relay
   relay_ret_pin: 17                  # Retract relay
   i2c_bus: 1                        # Current sensor bus
   ina_addr: 0x45                    # Current sensor address
   # ... other settings
   ```

3. **Install as System Service**
   ```bash
   sudo cp systemd/actuator.service /etc/systemd/system/
   sudo systemctl enable actuator.service
   sudo systemctl start actuator.service
   ```

4. **Verify Installation**
   ```bash
   sudo systemctl status actuator.service
   curl http://localhost:5000/status
   ```

### In Your UI Application

1. **Copy Client Library**
   ```bash
   cp users/examples/microservice_client.py your_ui_project/
   ```

2. **Install Dependencies**
   ```bash
   # Your UI project requirements
   pip install requests  # If using HTTP requests
   ```

## 🔌 API Reference

### Base URL
- **Local (on Pi)**: `http://localhost:5000`
- **Remote (via SSH)**: `ssh pi@<pi-ip> "curl http://localhost:5000/..."`

### Endpoints

#### `GET /status`
Get complete system status.

**Response:**
```json
{
  "current_position": 3,
  "is_moving": false
}
```

#### `GET /position` 
Get current position only.

**Response:**
```json
{
  "position": 3
}
```

#### `POST /move`
Move sash to specified position.

**Request:**
```json
{
  "position": 3
}
```

**Response (Success):**
```json
{
  "message": "Moving to position 3"
}
```

**Response (Error):**
```json
{
  "error": "Invalid position. Must be an integer between 1 and 5."
}
```

**Response (Busy):**
```json
{
  "message": "Actuator is already moving."
}
```

#### `POST /stop`
Emergency stop current movement.

**Response:**
```json
{
  "message": "Stop command issued."
}
```

## 🐍 Python Client Usage

### Basic Integration

```python
from microservice_client import FumeHoodSashClient

# Initialize client
sash = FumeHoodSashClient('192.168.1.100')  # Your Pi's IP

# Check connection
if sash.ping():
    print("✅ Fume hood microservice is online")
else:
    print("❌ Cannot reach microservice")
    
# Get current status
status = sash.get_status()
print(f"Position: {status['current_position']}")
print(f"Moving: {status['is_moving']}")

# Move to position (asynchronous)
response = sash.move_to_position(3)
if 'error' not in response:
    print("✅ Move command sent")
else:
    print(f"❌ Move failed: {response['error']}")

# Emergency stop
sash.stop()
```

### Advanced Operations

```python
# Move and wait for completion
try:
    final_status = sash.move_and_wait(position=5, timeout=30)
    print(f"✅ Movement complete: position {final_status['current_position']}")
except Exception as e:
    print(f"❌ Movement failed: {e}")

# Poll status during movement
sash.move_to_position(2)
while sash.is_moving():
    current_pos = sash.get_position()
    print(f"Moving... current position: {current_pos}")
    time.sleep(1)
```

### Workflow Integration Example

```python
class LabWorkflow:
    def __init__(self, fume_hood_ip):
        self.fume_hood = FumeHoodSashClient(fume_hood_ip)
    
    def prepare_experiment(self):
        """Prepare fume hood for experiment setup"""
        try:
            # Open hood for equipment setup
            print("🔓 Opening fume hood for setup...")
            self.fume_hood.move_and_wait(position=5, timeout=30)
            
            # User can now set up equipment
            input("Press Enter when setup is complete...")
            
            # Close for safety during experiment
            print("🔒 Closing fume hood for experiment...")
            self.fume_hood.move_and_wait(position=1, timeout=30)
            
            return {"status": "ready", "hood_position": 1}
            
        except Exception as e:
            # Emergency stop on any error
            self.fume_hood.stop()
            raise Exception(f"Preparation failed: {e}")
    
    def cleanup_experiment(self):
        """Open hood for cleanup"""
        print("🧹 Opening fume hood for cleanup...")
        return self.fume_hood.move_and_wait(position=4, timeout=30)
```

## 🔐 SSH Control Methods

### 1. Direct SSH Commands

```bash
# Check status
ssh pi@192.168.1.100 "curl -s http://localhost:5000/status | jq ."

# Move to position 3
ssh pi@192.168.1.100 "curl -X POST http://localhost:5000/move -H 'Content-Type: application/json' -d '{\"position\": 3}'"

# Emergency stop
ssh pi@192.168.1.100 "curl -X POST http://localhost:5000/stop"

# Check service status
ssh pi@192.168.1.100 "systemctl status actuator.service"
```

### 2. SSH Tunnel (for Direct API Access)

```bash
# Create SSH tunnel
ssh -L 5000:localhost:5000 pi@192.168.1.100

# Now use API directly from your machine
curl http://localhost:5000/status
curl -X POST http://localhost:5000/move -H "Content-Type: application/json" -d '{"position": 3}'
```

### 3. Bash Control Script

Use the provided `src/hood_sash_automation/api/ssh_control.sh`:

```bash
# Make executable
chmod +x src/hood_sash_automation/api/ssh_control.sh

# Usage examples
./src/hood_sash_automation/api/ssh_control.sh 192.168.1.100 status
./src/hood_sash_automation/api/ssh_control.sh 192.168.1.100 move 3
./src/hood_sash_automation/api/ssh_control.sh 192.168.1.100 stop
./src/hood_sash_automation/api/ssh_control.sh 192.168.1.100 logs
./src/hood_sash_automation/api/ssh_control.sh 192.168.1.100 restart
```

## 🔧 Configuration

### Hardware Configuration (`users/config/actuator_config.yaml`)

```yaml
# GPIO Pins (BCM numbering)
hall_pins: [5, 6, 13, 19, 26]       # Hall effect position sensors
relay_ext_pin: 27                    # Relay for extending (UP)
relay_ret_pin: 17                    # Relay for retracting (DOWN)

# Physical Buttons (optional)
buttons:
  up_pin: 23
  down_pin: 24
  stop_pin: 25

# I2C Current Sensor (INA219)
i2c_bus: 1
ina_addr: 0x45
r_shunt: 0.1                         # Shunt resistor (Ohms)
i_max: 3.0                           # Max current (Amps)

# Safety & Movement Settings
current_threshold_up: 1300           # Collision detection (up)
current_threshold_down: -1300        # Collision detection (down)
max_movement_time: 10.0              # Max time per movement (seconds)
position_timeout: 2.0                # Max time between positions (seconds)
bounce_ms: 10                        # Hall sensor debounce (ms)

# File Paths
position_state_file: "/tmp/position_state"
log_dir: "/var/log/sash_actuator"
```

### Client Configuration

```python
# Custom configuration
client = FumeHoodSashClient(
    pi_ip='192.168.1.100',
    username='pi',          # SSH username
    port=5000              # API port on Pi
)
```

## 🛡️ Security Considerations

### SSH Security
- **Use SSH keys** instead of passwords:
  ```bash
  ssh-keygen -t ed25519
  ssh-copy-id pi@192.168.1.100
  ```

- **Restrict SSH access** in `/etc/ssh/sshd_config`:
  ```
  PermitRootLogin no
  PasswordAuthentication no
  AllowUsers pi
  ```

### Network Security
- API runs on `localhost` only (not accessible from network)
- All external access goes through encrypted SSH
- No open ports on the Pi (except SSH port 22)

### Physical Safety
- Built-in collision detection via current monitoring
- Emergency stop functionality always available
- Movement timeouts prevent runaway conditions
- Physical stop button support

## 📊 Monitoring & Troubleshooting

### Service Status
```bash
# Check service status
ssh pi@your-pi "systemctl status actuator.service"

# View recent logs
ssh pi@your-pi "journalctl -u actuator.service -n 50"

# Restart service
ssh pi@your-pi "sudo systemctl restart actuator.service"
```

### API Health Check
```python
# Test connectivity
client = FumeHoodSashClient('192.168.1.100')
if client.ping():
    print("✅ Service is healthy")
else:
    print("❌ Service is not responding")
```

### Common Issues

**Issue: SSH connection refused**
```bash
# Check SSH service on Pi
ssh pi@your-pi "systemctl status ssh"
```

**Issue: API not responding**
```bash
# Check if Flask app is running
ssh pi@your-pi "ps aux | grep python"
ssh pi@your-pi "netstat -tlnp | grep 5000"
```

**Issue: Hardware not responding**
```bash
# Check GPIO permissions
ssh pi@your-pi "ls -la /dev/gpiomem"
ssh pi@your-pi "groups pi"  # Should include 'gpio' group
```

## 🚀 Development & Testing

### Local Testing (Docker)
Use the provided Docker testing environment:

```bash
# Setup local testing
./docker-test/scripts/setup_local_only.sh

# Run tests
./docker-test/scripts/test_local.sh unit        # Fast unit tests
./docker-test/scripts/test_local.sh integration # Component integration
./docker-test/scripts/test_local.sh all         # Full test suite
```

### Device Testing
Test on actual hardware:

```bash
# Run smoke tests on Pi
python device-test/smoke_tests.py
```

### Client Testing
Test the microservice client:

```bash
# Basic connectivity test
python users/examples/microservice_client.py 192.168.1.100

# Advanced testing with movement
python users/examples/ssh_client_example.py 192.168.1.100 sequence
```

## 📚 Integration Examples

### Web Application (Flask/FastAPI)
```python
from flask import Flask, jsonify, request
from microservice_client import FumeHoodSashClient

app = Flask(__name__)
fume_hood = FumeHoodSashClient('192.168.1.100')

@app.route('/lab/fume-hood/status')
def get_hood_status():
    try:
        status = fume_hood.get_status()
        return jsonify(status)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/lab/fume-hood/move', methods=['POST'])
def move_hood():
    data = request.json
    position = data.get('position')
    
    try:
        response = fume_hood.move_to_position(position)
        return jsonify(response)
    except Exception as e:
        return jsonify({"error": str(e)}), 400
```

### Workflow Automation
```python
import asyncio
from microservice_client import FumeHoodSashClient

class LabAutomation:
    def __init__(self):
        self.fume_hood = FumeHoodSashClient('192.168.1.100')
        self.spectrometer = SpectrometerClient('192.168.1.101')
        self.robot_arm = RobotArmClient('192.168.1.102')
    
    async def run_experiment_sequence(self):
        """Automated experiment workflow"""
        try:
            # 1. Prepare workspace
            await self.prepare_workspace()
            
            # 2. Run experiment
            results = await self.execute_experiment()
            
            # 3. Cleanup
            await self.cleanup_workspace()
            
            return results
            
        except Exception as e:
            # Emergency stop all equipment
            self.emergency_stop_all()
            raise
    
    async def prepare_workspace(self):
        """Open hood, position robot, initialize instruments"""
        print("🔧 Preparing workspace...")
        
        # Open fume hood for setup
        self.fume_hood.move_and_wait(position=5, timeout=30)
        
        # Position robot arm
        await self.robot_arm.move_to_home()
        
        # Initialize spectrometer
        await self.spectrometer.calibrate()
        
        print("✅ Workspace ready")
    
    def emergency_stop_all(self):
        """Stop all equipment immediately"""
        self.fume_hood.stop()
        self.robot_arm.emergency_stop()
        self.spectrometer.abort()
```

## 📋 API Client Library Reference

### FumeHoodSashClient Class

#### Constructor
```python
FumeHoodSashClient(pi_ip: str, username: str = 'pi', port: int = 5000)
```

#### Methods

| Method | Description | Returns |
|--------|-------------|---------|
| `ping()` | Test connectivity | `bool` |
| `get_status()` | Get full status | `Dict[str, Union[int, bool]]` |
| `get_position()` | Get position only | `Optional[int]` |
| `move_to_position(position)` | Move to position 1-5 | `Dict[str, str]` |
| `stop()` | Emergency stop | `Dict[str, str]` |
| `is_moving()` | Check if moving | `bool` |
| `wait_for_movement_complete(timeout)` | Wait for completion | `bool` |
| `move_and_wait(position, timeout)` | Move and wait | `Dict[str, Union[int, bool]]` |

#### Error Handling
All methods raise `Exception` on errors. Wrap calls in try-catch blocks:

```python
try:
    status = client.get_status()
except Exception as e:
    print(f"Error communicating with fume hood: {e}")
```

## 🔗 Related Documentation

- **Hardware Setup**: See `README.md` for physical installation
- **Docker Testing**: See `docker-test/README.md` for development environment  
- **Device Testing**: See `device-test/README.md` for on-device validation
- **Configuration**: See `users/config/actuator_config.yaml` for all settings
- **SSH Control Script**: See `src/hood_sash_automation/api/ssh_control.sh` for bash automation
- **Client Libraries**: See `users/examples/microservice_client.py` and `users/examples/ssh_client_example.py`

---

**🎯 Your fume hood is now ready to integrate as a microservice into any workflow automation system!** 