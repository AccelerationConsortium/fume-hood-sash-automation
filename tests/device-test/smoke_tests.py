#!/usr/bin/env python3
"""
Smoke Tests for Real Device Testing
===================================

Run these tests on the actual Raspberry Pi with real hardware.
These are minimal tests to verify basic functionality works.

Usage:
    python tests/device-test/smoke_tests.py
    python tests/device-test/smoke_tests.py --component actuator
    python tests/device-test/smoke_tests.py --component sensor
"""

import argparse
import sys
import time
import logging
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]

# Add src to path for imports when running directly from the repo checkout.
sys.path.insert(0, str(ROOT_DIR / "src"))

def setup_logging():
    """Set up logging for device tests."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [DEVICE-TEST] %(levelname)s: %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(ROOT_DIR / "tests" / "device-test" / "smoke_test.log")
        ]
    )

def test_gpio_access():
    """Test basic GPIO access."""
    logging.info("Testing GPIO access...")
    try:
        import RPi.GPIO as GPIO
        GPIO.setmode(GPIO.BCM)
        # Test a safe pin (GPIO 18)
        GPIO.setup(18, GPIO.OUT)
        GPIO.output(18, GPIO.HIGH)
        time.sleep(0.1)
        GPIO.output(18, GPIO.LOW)
        GPIO.cleanup()
        logging.info("GPIO access working")
        return True
    except Exception as e:
        logging.error(f"GPIO access failed: {e}")
        return False

def test_i2c_access():
    """Test basic I2C access."""
    logging.info("Testing I2C access...")
    try:
        import smbus2
        bus = smbus2.SMBus(1)  # I2C bus 1
        # Just test bus creation, don't access devices
        bus.close()
        logging.info("I2C access working")
        return True
    except Exception as e:
        logging.error(f"I2C access failed: {e}")
        return False

def test_actuator_import():
    """Test actuator module imports."""
    logging.info("Testing actuator imports...")
    try:
        from hood_sash_automation.actuator.controller import SashActuator
        from hood_sash_automation.actuator.relay import ActuatorRelay
        from hood_sash_automation.actuator.switches import HallArray
        from hood_sash_automation.actuator.current import CurrentSensor
        logging.info("Actuator imports working")
        return True
    except Exception as e:
        logging.error(f"Actuator import failed: {e}")
        return False

def test_sensor_import():
    """Test sensor module imports."""
    logging.info("Testing sensor imports...")
    try:
        from hood_sash_automation.sensor.sensor import SashSensor
        assert SashSensor is not None
        logging.info("Sensor imports working")
        return True
    except Exception as e:
        logging.error(f"Sensor import failed: {e}")
        return False

def test_config_loading():
    """Test configuration file loading."""
    logging.info("Testing config loading...")
    try:
        import yaml

        # Test actuator config
        with open(ROOT_DIR / "users" / "config" / "actuator_config.yaml", 'r') as f:
            actuator_config = yaml.safe_load(f)
        assert 'relay_ext_pin' in actuator_config
        assert 'hall_pins' in actuator_config
        assert 'i2c_bus' in actuator_config

        # Test sensor config
        with open(ROOT_DIR / "users" / "config" / "sensor_config.yaml", 'r') as f:
            sensor_config = yaml.safe_load(f)
        assert 'hall_sensor_pin' in sensor_config
        assert 'led_pin' in sensor_config

        logging.info("Config loading working")
        return True
    except Exception as e:
        logging.error(f"Config loading failed: {e}")
        return False

def test_actuator_hardware_init():
    """Test actuator hardware initialization (safe operations only)."""
    logging.info("Testing actuator hardware initialization...")
    try:
        import yaml
        with open(ROOT_DIR / "users" / "config" / "actuator_config.yaml", 'r') as f:
            config = yaml.safe_load(f)

        # Test relay initialization (but don't activate)
        from hood_sash_automation.actuator.relay import ActuatorRelay
        relay = ActuatorRelay(config['relay_ext_pin'], config['relay_ret_pin'])
        relay.all_off()  # Safe operation

        # Test hall sensor initialization
        from hood_sash_automation.actuator.switches import HallArray
        hall = HallArray(config['hall_pins'], bouncetime=config['bounce_ms'])
        states = hall.snapshot()  # Safe read operation
        hall.close()

        logging.info(f"Actuator hardware init working (Hall states: {states})")
        return True
    except Exception as e:
        logging.error(f"Actuator hardware init failed: {e}")
        return False

def test_sensor_hardware_init():
    """Test sensor hardware initialization."""
    logging.info("Testing sensor hardware initialization...")
    try:
        import yaml
        with open(ROOT_DIR / "users" / "config" / "sensor_config.yaml", 'r') as f:
            config = yaml.safe_load(f)

        from hood_sash_automation.sensor.sensor import SashSensor
        # Use individual config parameters rather than whole config dict
        sensor = SashSensor(config['hall_sensor_pin'], config['led_pin'])

        state = sensor.get_current_state()
        sensor.cleanup()
        logging.info(f"Sensor hardware init working (magnet_present: {state})")
        return True

    except Exception as e:
        logging.error(f"Sensor hardware init failed: {e}")
        return False

def run_all_smoke_tests():
    """Run all smoke tests."""
    tests = [
        ("Basic GPIO", test_gpio_access),
        ("Basic I2C", test_i2c_access),
        ("Actuator Imports", test_actuator_import),
        ("Sensor Imports", test_sensor_import),
        ("Config Loading", test_config_loading),
        ("Actuator Hardware", test_actuator_hardware_init),
        ("Sensor Hardware", test_sensor_hardware_init),
    ]

    results = []
    for test_name, test_func in tests:
        logging.info(f"\n{'='*50}")
        logging.info(f"Running: {test_name}")
        logging.info(f"{'='*50}")

        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            logging.error(f"{test_name} crashed: {e}")
            results.append((test_name, False))

    # Summary
    logging.info(f"\n{'='*50}")
    logging.info("SMOKE TEST SUMMARY")
    logging.info(f"{'='*50}")

    passed = 0
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        logging.info(f"{status} {test_name}")
        if result:
            passed += 1

    logging.info(f"\nResult: {passed}/{len(results)} tests passed")

    if passed == len(results):
        logging.info("All smoke tests PASSED! Device is ready.")
        return True
    else:
        logging.error("Some smoke tests FAILED! Check device setup.")
        return False

def run_component_tests(component):
    """Run tests for specific component."""
    if component == "actuator":
        tests = [
            ("Basic GPIO", test_gpio_access),
            ("Basic I2C", test_i2c_access),
            ("Actuator Imports", test_actuator_import),
            ("Config Loading", test_config_loading),
            ("Actuator Hardware", test_actuator_hardware_init),
        ]
    elif component == "sensor":
        tests = [
            ("Basic GPIO", test_gpio_access),
            ("Sensor Imports", test_sensor_import),
            ("Config Loading", test_config_loading),
            ("Sensor Hardware", test_sensor_hardware_init),
        ]
    else:
        logging.error(f"Unknown component: {component}")
        return False

    results = []
    for test_name, test_func in tests:
        logging.info(f"Running: {test_name}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            logging.error(f"{test_name} crashed: {e}")
            results.append((test_name, False))

    passed = sum(1 for _, result in results if result)
    logging.info(f"\n{component.title()} tests: {passed}/{len(results)} passed")
    return passed == len(results)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run smoke tests on real device")
    parser.add_argument("--component", choices=["actuator", "sensor"],
                       help="Test specific component only")
    args = parser.parse_args()

    setup_logging()
    logging.info("Starting smoke tests on real device...")
    logging.info(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    if args.component:
        success = run_component_tests(args.component)
    else:
        success = run_all_smoke_tests()

    sys.exit(0 if success else 1)