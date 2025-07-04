# Device Testing
## Real Hardware Testing on Raspberry Pi

This directory contains tests that run on the actual Raspberry Pi with real hardware components.

## 🚀 Quick Start

### On your Raspberry Pi:

```bash
# Run all smoke tests
python tests/device-test/smoke_tests.py

# Test specific component
python tests/device-test/smoke_tests.py --component actuator
python tests/device-test/smoke_tests.py --component sensor
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

## 🔌 Testing on Pi Zero 2W Without Connected Devices

### Perfect for Development & Validation

The smoke tests are specifically designed to be **safe** and work **without any ancillary devices** connected to your Pi Zero 2W. This is ideal for:

- **Code Validation**: Verify your code runs correctly on ARM architecture
- **Environment Testing**: Confirm Pi setup and dependencies work
- **Pre-Hardware Testing**: Validate everything before connecting expensive devices
- **Development Setup**: Test changes without risking hardware damage

### Quick Start on Pi Zero 2W (No Hardware Required):

```bash
# SSH into your Pi Zero 2W
ssh pi@your-pi-ip

# Clone/update the project
git clone <your-repo> fume-hood-sash-automation
cd fume-hood-sash-automation
# OR: git pull (if already cloned)

# Install dependencies
pip install -e .[actuator,sensor]

# Run all smoke tests (safe for disconnected hardware)
python tests/device-test/smoke_tests.py

# Or test specific components
python tests/device-test/smoke_tests.py --component actuator
python tests/device-test/smoke_tests.py --component sensor
```

### ✅ Safe Operations (Work Without Connected Devices)

The smoke tests perform **minimal, safe operations** that won't damage anything:

- **GPIO Access**: Test basic pin control on GPIO 18 (safe pin)
- **I2C Bus**: Just test bus creation, don't access specific devices  
- **Module Imports**: Verify all Python modules load correctly on Pi
- **Config Loading**: Check YAML configuration files are valid
- **Hardware Init**: Initialize hardware classes without activation
- **Relay Setup**: Configure relay pins but don't activate motors
- **Hall Sensor Read**: Read pin states (will show "no sensors detected")

### ❌ What They DON'T Do (Avoid Hardware Damage)

- Don't activate motors or relays with real loads
- Don't try to move actual hardware
- Don't perform complex integration tests  
- Don't stress test or run continuously
- Don't attempt to read from unconnected I2C devices

### 📊 Expected Output on Pi Zero 2W (No Devices)

**With no devices connected, you should see:**

```bash
🚀 Starting smoke tests on real device...
==================================================
Running: Basic GPIO
==================================================
✅ GPIO access working

==================================================
Running: Basic I2C  
==================================================
✅ I2C access working

==================================================
Running: Actuator Imports
==================================================
✅ Actuator imports working

==================================================
Running: Sensor Imports
==================================================  
✅ Sensor imports working

==================================================
Running: Config Loading
==================================================
✅ Config loading working

==================================================
Running: Actuator Hardware
==================================================
✅ Actuator hardware init working (Hall states: [1, 1, 1, 1, 1])

==================================================
Running: Sensor Hardware
==================================================
⚠️ Sensor init OK but read failed: No sensor detected

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

### 🎯 What This Validates on Pi Zero 2W

Running these tests confirms:

1. **Pi Environment**: RPi.GPIO and smbus2 libraries work correctly
2. **Code Quality**: All Python modules import without errors on ARM
3. **Configuration**: YAML files are valid and loadable
4. **Hardware Access**: GPIO and I2C interfaces are accessible
5. **Initialization**: Hardware classes can be created safely
6. **Pi Compatibility**: Code runs correctly on ARM64 architecture
7. **Memory Usage**: Application fits within Pi Zero 2W's 512MB RAM

### 🔧 Pi Zero 2W Specific Setup

**Enable Required Interfaces:**
```bash
sudo raspi-config
# → Interface Options → I2C → Enable
# → Interface Options → SPI → Enable (if needed)
# → Interface Options → SSH → Enable (for remote access)
```

**Memory Optimization (if needed):**
```bash
# If you get memory warnings, enable swap
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile  # Set CONF_SWAPSIZE=512
sudo dphys-swapfile setup
sudo dphys-swapfile swapon
```

**Permissions Setup:**
```bash
# Add user to gpio group (avoid running as root)
sudo usermod -a -G gpio $USER
sudo usermod -a -G i2c $USER

# Logout and login again for changes to take effect
```

### 🔄 Complete Testing Workflow

#### **Development Phase** (on your laptop):
```bash
# Run comprehensive tests with mocked hardware
./tests/docker-test/scripts/setup_local_only.sh
./tests/docker-test/scripts/test_local.sh all
```

#### **Pi Validation Phase** (Pi Zero 2W, no devices):
```bash
# Deploy to Pi and validate environment
git push origin main
ssh pi@your-pi-ip "cd fume-hood && git pull"
ssh pi@your-pi-ip "cd fume-hood && python tests/device-test/smoke_tests.py"
```

#### **Hardware Integration Phase** (with devices connected):
```bash
# Only run when you have actual hardware connected
ssh pi@your-pi-ip "cd fume-hood && sudo systemctl start actuator sensor"
```

This three-phase approach lets you:
1. **Develop confidently** with full test coverage
2. **Validate Pi compatibility** without hardware risk  
3. **Deploy safely** knowing everything works

The smoke tests typically complete in **under 30 seconds** on Pi Zero 2W and give you confidence that everything will work when you do connect the actual sensors, motors, and other components.

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
- Review users/config/actuator_config.yaml and users/config/sensor_config.yaml

## 📁 File Structure

```
device-test/
├── smoke_tests.py      # Main smoke test script (required)
├── api_service_test.py # API service testing (optional)
├── smoke_test.log      # Test execution log  
├── api_test.log        # API test execution log
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

## 🔧 Do You Need Additional Test Scripts?

### ✅ **For Basic Pi Zero 2W Validation: `smoke_tests.py` is sufficient**

The smoke tests cover 95% of what you need to validate before connecting hardware:
- Code compatibility on ARM architecture
- Environment validation (GPIO/I2C access)
- Python module imports
- Configuration file loading
- Basic hardware initialization

**This is all you need for most scenarios.**

### 🔧 **Optional: Additional Testing Scripts**

#### **API Service Testing** (Optional)

If you want to test that Flask services can start and respond:

```bash
# Install requests dependency for API testing
pip install requests

# Test API services (optional - takes 30-60 seconds)
python device-test/api_service_test.py

# Test specific service
python device-test/api_service_test.py --service actuator
python device-test/api_service_test.py --service sensor
```

**When to use:**
- Testing Flask service startup on Pi Zero 2W
- Validating API endpoints respond correctly
- Checking port binding and memory usage
- Before deploying microservices

#### **Docker Testing on Pi** (Optional)

For comprehensive testing with Docker:

```bash
# Pi-optimized Docker testing (requires Docker on Pi)
./docker-test/scripts/run_rpi_tests.sh quick

# Hardware validation with Docker
./docker-test/scripts/run_rpi_tests.sh hardware
```

**When to use:**
- Want full test suite on Pi hardware
- Testing with resource constraints
- Validating Docker deployment

### 📊 **Testing Comparison**

| Test Type | Duration | Coverage | When to Use |
|-----------|----------|----------|-------------|
| **smoke_tests.py** | 30s | Basic validation | **Always** - before hardware connection |
| **api_service_test.py** | 60s | API services | Optional - if using microservices |
| **Docker tests** | 5-10min | Full suite | Optional - comprehensive validation |

### 🎯 **Recommended Workflow**

#### **Quick Validation** (most common):
```bash
# Basic validation (sufficient for most cases)
python device-test/smoke_tests.py
```

#### **Complete Validation** (before production):
```bash
# 1. Basic validation
python device-test/smoke_tests.py

# 2. API service validation (if using microservices)
python device-test/api_service_test.py

# 3. Start services if tests pass
sudo systemctl start actuator sensor
```

#### **Development Workflow**:
```bash
# Local development
./docker-test/scripts/test_local.sh integration

# Deploy to Pi
git push && ssh pi@your-pi "cd fume-hood && git pull"

# Validate on Pi (basic)
ssh pi@your-pi "cd fume-hood && python device-test/smoke_tests.py"

# Deploy if smoke tests pass
ssh pi@your-pi "sudo systemctl start actuator sensor"
```

**Bottom line:** Start with `smoke_tests.py` - it covers everything you need for basic Pi Zero 2W validation without connected devices. Add other tests only if you need them for specific scenarios. 