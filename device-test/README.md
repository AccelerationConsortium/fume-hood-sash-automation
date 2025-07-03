# Device Testing
## Real Hardware Testing on Raspberry Pi

This directory contains tests that run on the actual Raspberry Pi with real hardware components.

## 🚀 Quick Start

### On your Raspberry Pi:

```bash
# Run all smoke tests
python device-test/smoke_tests.py

# Test specific component
python device-test/smoke_tests.py --component actuator
python device-test/smoke_tests.py --component sensor
```

## 🧪 What Are Smoke Tests?

Smoke tests are **minimal tests that verify basic functionality**:
- ✅ Hardware can be accessed (GPIO, I2C)
- ✅ Code imports work on real Pi
- ✅ Configuration files load correctly
- ✅ Basic hardware initialization succeeds

**They DON'T test:**
- Complex business logic (that's in docker-test/)
- Full integration scenarios
- Performance or stress testing

## 📋 Test Categories

### Basic Hardware Access
- **GPIO**: Test basic pin control
- **I2C**: Test I2C bus access
- **Imports**: Verify all modules load on Pi

### Component Initialization  
- **Actuator**: Relay setup, Hall sensor reading
- **Sensor**: Distance sensor initialization
- **Config**: YAML configuration loading

## 🔄 Typical Workflow

### 1. Development (Local Machine):
```bash
# Run comprehensive tests in Docker
./docker-test/scripts/setup_local_only.sh
./docker-test/scripts/test_local.sh all
```

### 2. Deploy to Pi:
```bash
# Copy code to Pi
scp -r . pi@your-pi-ip:/home/pi/fume-hood-sash-automation/

# Or use git
git push origin main
# Then on Pi: git pull
```

### 3. Smoke Test on Pi:
```bash
# SSH into Pi
ssh pi@your-pi-ip

# Run smoke tests
cd fume-hood-sash-automation
python device-test/smoke_tests.py
```

### 4. Deploy Services:
```bash
# If smoke tests pass, start the services
sudo systemctl start actuator sensor
```

## 🎯 When to Run Device Tests

- **After code changes**: Verify new code works on real hardware
- **After Pi updates**: Ensure OS/library updates didn't break anything  
- **Before production**: Final validation before deployment
- **Troubleshooting**: Isolate hardware vs software issues

## 📊 Expected Output

### Successful Run:
```
🚀 Starting smoke tests on real device...
==================================================
Running: Basic GPIO
==================================================
✅ GPIO access working
...
==================================================
SMOKE TEST SUMMARY
==================================================
✅ PASS Basic GPIO
✅ PASS Basic I2C  
✅ PASS Actuator Imports
✅ PASS Sensor Imports
✅ PASS Config Loading
✅ PASS Actuator Hardware
✅ PASS Sensor Hardware

Result: 7/7 tests passed
🎉 All smoke tests PASSED! Device is ready.
```

### Failed Run:
```
❌ I2C access failed: [Errno 2] No such file or directory: '/dev/i2c-1'
...
Result: 5/7 tests passed
💥 Some smoke tests FAILED! Check device setup.
```

## 🛠️ Troubleshooting

### Common Issues:

**"No such file or directory: '/dev/i2c-1'"**
- Enable I2C: `sudo raspi-config` → Interface Options → I2C → Enable

**"Permission denied accessing GPIO"**  
- Run as root: `sudo python device-test/smoke_tests.py`
- Or add user to gpio group: `sudo usermod -a -G gpio $USER`

**"Module not found"**
- Install dependencies: `pip install -e .[actuator,sensor]`
- Check Python path in smoke_tests.py

**Hardware not responding**
- Check physical connections
- Verify power supply
- Review config/actuator_config.yaml and config/sensor_config.yaml

## 📁 File Structure

```
device-test/
├── smoke_tests.py      # Main smoke test script
├── smoke_test.log      # Test execution log  
└── README.md          # This file

# Future expansion:
├── integration/        # Real hardware integration tests
├── calibration/        # Sensor calibration tests
├── stress/            # Long-running reliability tests  
└── scripts/           # Device-specific utilities
```

## 🎛️ Advanced Usage

### Run Specific Test Functions:
```python
# Interactive Python session
python3
>>> from device_test.smoke_tests import *
>>> setup_logging()
>>> test_actuator_hardware_init()
```

### Automated Device Testing:
```bash
# Add to cron for periodic health checks
0 */6 * * * cd /home/pi/fume-hood-sash-automation && python device-test/smoke_tests.py >> /var/log/device-health.log 2>&1
```

## 🔗 Integration with Docker Testing

This device testing complements your Docker-based testing:

| Test Type | Where | What | Speed |
|-----------|-------|------|-------|
| **Unit/Integration** | Docker (local) | Business logic, mocked hardware | Fast (seconds) |
| **Smoke Tests** | Pi (device) | Hardware access, basic init | Fast (30s) |  
| **Full Validation** | Pi (manual) | Complete system testing | Slow (manual) |

The combination gives you confidence that both your **code logic** (Docker) and **hardware integration** (Pi) work correctly! 