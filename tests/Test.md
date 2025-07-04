# Testing Documentation

This project uses a **comprehensive three-layer testing approach**:

1. **Local Docker Testing**: Fast development testing with mocked hardware
2. **Pi Zero 2W Testing**: Safe validation on real Pi hardware **without connected devices**
3. **Hardware Integration**: Full testing with connected sensors and actuators

## 🚀 Quick Start Testing

### **Development Testing** (on your laptop)
```bash
# Set up local Docker testing (one-time)
./tests/docker-test/scripts/setup_local_only.sh

# Quick integration test (recommended - 5-10s)
./tests/docker-test/scripts/test_local.sh integration

# If integration passes, run full tests (30s)
./tests/docker-test/scripts/test_local.sh all
```

### **Pi Zero 2W Testing** (safe, no hardware required)
```bash
# Deploy to Pi Zero 2W
git push && ssh pi@your-pi-ip "cd fume-hood && git pull"

# Basic validation (30s - covers 95% of Pi compatibility)
ssh pi@your-pi-ip "cd fume-hood && python tests/device-test/smoke_tests.py"

# Optional: API service testing (60s - if using microservices)
ssh pi@your-pi-ip "cd fume-hood && python tests/device-test/api_service_test.py"
```

### **Hardware Integration** (with connected devices)
```bash
# Only after Pi testing passes - start services with real hardware
ssh pi@your-pi-ip "sudo systemctl start actuator sensor"
```

## 🎯 Testing Strategy

| Test Layer | Where | Duration | Coverage | Safety |
|------------|-------|----------|----------|---------|
| **Docker Tests** | Local laptop | 5-30s | Business logic, mocked hardware | ✅ Completely safe |
| **Pi Device Tests** | Pi Zero 2W | 30-60s | ARM compatibility, GPIO/I2C access | ✅ Safe without devices |
| **Hardware Tests** | Pi + devices | Manual | Full integration | ⚠️ Requires connected hardware |

## 🔧 Pi Zero 2W Testing Without Hardware

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
python tests/device-test/smoke_tests.py
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

## 📚 Detailed Testing Documentation

### Docker Testing
- **[Docker Testing Guide](docker-test/README.md)** - Local development testing with mocked hardware
- Fast iteration and development testing
- Completely safe for development environments
- Covers business logic and API endpoints

### Device Testing
- **[Device Testing Guide](device-test/README.md)** - Pi Zero 2W testing without connected devices
- Real Pi hardware validation
- GPIO/I2C access verification
- ARM compatibility testing

### Hardware Integration Testing
- **[Pi Hardware Setup](device-test/README.md#pi-zero-2w-specific-setup)** - Interface configuration and optimization
- Full system integration with connected devices
- Real sensor and actuator testing
- Production deployment validation

## Test Structure

```
tests/
├── Test.md                 # This documentation file
├── docker-test/           # Local Docker testing
│   ├── README.md         # Docker testing guide
│   ├── scripts/          # Testing scripts
│   └── tests/           # Test files
├── device-test/          # Pi device testing
│   ├── README.md        # Device testing guide
│   ├── smoke_tests.py   # Quick Pi validation
│   └── api_service_test.py  # API service testing
```

## Testing Best Practices

1. **Always start with Docker tests** - Quick feedback for development
2. **Test on Pi Zero 2W before hardware** - Validate ARM compatibility safely
3. **Use smoke tests for quick validation** - Cover 95% of compatibility issues
4. **Only connect hardware after Pi tests pass** - Prevent expensive device damage
5. **Run full test suite before deployment** - Ensure production readiness

## Troubleshooting

### Common Issues

#### Docker Tests
- **Permission errors**: Check Docker daemon is running and user has permissions
- **Import errors**: Ensure all dependencies are installed in the test environment

#### Pi Device Tests
- **GPIO/I2C access**: Ensure user is in `gpio` and `i2c` groups
- **Module not found**: Check virtual environment is activated
- **Permission denied**: Use correct user for GPIO access (not root)

#### Hardware Integration
- **Device not responding**: Check physical connections and power
- **Current sensor errors**: Verify I2C address and wiring
- **Motor not moving**: Check relay connections and power supply

### Getting Help

If you encounter issues:
1. Check the specific README.md files in each test directory
2. Review the main project documentation
3. Verify hardware connections and configuration files
4. Check system logs for detailed error messages 