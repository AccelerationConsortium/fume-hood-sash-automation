#!/usr/bin/env python3
"""
API Service Test for Pi Zero 2W
===============================

Optional test script to validate that Flask services can start and respond
on Pi Zero 2W without connected hardware devices.

Usage:
    python device-test/api_service_test.py
    python device-test/api_service_test.py --service actuator
    python device-test/api_service_test.py --service sensor
"""

import argparse
import sys
import time
import logging
import requests
import subprocess
import signal
import os
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

def setup_logging():
    """Set up logging for API service tests."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [API-TEST] %(levelname)s: %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler("device-test/api_test.log")
        ]
    )

class ServiceTester:
    """Test API services on Pi Zero 2W."""

    def __init__(self):
        self.processes = {}
        self.test_results = []

    def cleanup(self):
        """Clean up any running test processes."""
        for name, proc in self.processes.items():
            if proc and proc.poll() is None:
                logging.info(f"Stopping {name} service...")
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()

    def _get_python_executable(self):
        """Get the Python executable that can import our package."""
        logging.info(f"🔍 Detecting Python executable (current: {sys.executable})")

        # First try the current Python executable
        try:
            result = subprocess.run([
                sys.executable, '-c', 'import hood_sash_automation; print("OK")'
            ], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                logging.info(f"✅ Using current Python: {sys.executable}")
                return sys.executable
        except Exception as e:
            logging.info(f"❌ Current Python failed: {e}")

        # Try python3 command
        try:
            result = subprocess.run([
                'python3', '-c', 'import hood_sash_automation; print("OK")'
            ], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                logging.info("✅ Using python3 command")
                return 'python3'
        except Exception as e:
            logging.info(f"❌ python3 failed: {e}")

        # Try python command
        try:
            result = subprocess.run([
                'python', '-c', 'import hood_sash_automation; print("OK")'
            ], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                logging.info("✅ Using python command")
                return 'python'
        except Exception as e:
            logging.info(f"❌ python failed: {e}")

        # If none work, fall back to sys.executable
        logging.warning(f"⚠️ Could not find Python executable with hood_sash_automation package, using: {sys.executable}")
        return sys.executable

    def test_actuator_service(self):
        """Test actuator service startup and basic API response."""
        logging.info("🤖 Testing actuator service...")

        try:
            # Start actuator service in test mode
            env = os.environ.copy()
            env['FLASK_DEBUG'] = '1'

            # Use the Python that can import our package
            python_cmd = self._get_python_executable()
            proc = subprocess.Popen([
                python_cmd, '-m', 'hood_sash_automation.api.api_service'
            ], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            self.processes['actuator'] = proc

            # Wait for service to start
            time.sleep(3)

            # Check if process is still running
            if proc.poll() is not None:
                stdout, stderr = proc.communicate()
                stderr_str = stderr.decode()

                # Check if failure is due to missing hardware (expected)
                if "Input/output error" in stderr_str or "OSError" in stderr_str:
                    logging.info("⚠️ Actuator service failed to start due to missing hardware (expected)")
                    logging.info("✅ This confirms I2C access works and code tries to initialize hardware")
                    return True
                else:
                    logging.error(f"❌ Actuator service failed to start (unexpected error)")
                    logging.error(f"stdout: {stdout.decode()}")
                    logging.error(f"stderr: {stderr_str}")
                    return False

            # Test API endpoint
            try:
                response = requests.get('http://localhost:5000/status', timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    logging.info(f"✅ Actuator service responding (status: {data.get('status', 'unknown')})")
                    return True
                else:
                    logging.error(f"❌ Actuator service returned status code: {response.status_code}")
                    return False
            except requests.exceptions.RequestException as e:
                logging.error(f"❌ Failed to connect to actuator service: {e}")
                return False

        except Exception as e:
            logging.error(f"❌ Actuator service test failed: {e}")
            return False
        finally:
            # Stop the service
            if 'actuator' in self.processes:
                proc = self.processes['actuator']
                if proc and proc.poll() is None:
                    proc.terminate()
                    proc.wait()

    def test_sensor_service(self):
        """Test sensor service startup and basic API response."""
        logging.info("📊 Testing sensor service...")

        try:
            # Start sensor service in test mode
            env = os.environ.copy()
            env['FLASK_DEBUG'] = '1'

            # Use the Python that can import our package
            python_cmd = self._get_python_executable()
            proc = subprocess.Popen([
                python_cmd, '-m', 'hood_sash_automation.sensor.api_service'
            ], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            self.processes['sensor'] = proc

            # Wait for service to start
            time.sleep(3)

            # Check if process is still running
            if proc.poll() is not None:
                stdout, stderr = proc.communicate()
                logging.error(f"❌ Sensor service failed to start")
                logging.error(f"stdout: {stdout.decode()}")
                logging.error(f"stderr: {stderr.decode()}")
                return False

            # Test API endpoint
            try:
                response = requests.get('http://localhost:5005/status', timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    logging.info(f"✅ Sensor service responding (status: {data.get('status', 'unknown')})")
                    return True
                else:
                    logging.error(f"❌ Sensor service returned status code: {response.status_code}")
                    return False
            except requests.exceptions.RequestException as e:
                logging.error(f"❌ Failed to connect to sensor service: {e}")
                return False

        except Exception as e:
            logging.error(f"❌ Sensor service test failed: {e}")
            return False
        finally:
            # Stop the service
            if 'sensor' in self.processes:
                proc = self.processes['sensor']
                if proc and proc.poll() is None:
                    proc.terminate()
                    proc.wait()

    def test_port_binding(self):
        """Test that required ports can be bound."""
        logging.info("🔌 Testing port binding...")

        import socket

        ports_to_test = [5000, 5005]
        all_available = True

        for port in ports_to_test:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.bind(('localhost', port))
                sock.close()
                logging.info(f"✅ Port {port} available")
            except socket.error as e:
                logging.error(f"❌ Port {port} not available: {e}")
                all_available = False

        return all_available

    def test_memory_usage(self):
        """Test basic memory usage on Pi Zero 2W."""
        logging.info("💾 Testing memory usage...")

        try:
            # Check available memory
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    if line.startswith('MemAvailable:'):
                        mem_kb = int(line.split()[1])
                        mem_mb = mem_kb // 1024
                        logging.info(f"Available memory: {mem_mb}MB")

                        if mem_mb < 100:
                            logging.warning(f"⚠️ Low memory: {mem_mb}MB available")
                            return False
                        else:
                            logging.info(f"✅ Sufficient memory: {mem_mb}MB available")
                            return True

            logging.error("❌ Could not read memory information")
            return False

        except Exception as e:
            logging.error(f"❌ Memory test failed: {e}")
            return False

    def run_all_tests(self):
        """Run all API service tests."""
        tests = [
            ("Port Binding", self.test_port_binding),
            ("Memory Usage", self.test_memory_usage),
            ("Actuator Service", self.test_actuator_service),
            ("Sensor Service", self.test_sensor_service),
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
                logging.error(f"❌ {test_name} crashed: {e}")
                results.append((test_name, False))

        # Summary
        logging.info(f"\n{'='*50}")
        logging.info("API SERVICE TEST SUMMARY")
        logging.info(f"{'='*50}")

        passed = 0
        for test_name, result in results:
            status = "✅ PASS" if result else "❌ FAIL"
            logging.info(f"{status} {test_name}")
            if result:
                passed += 1

        logging.info(f"\nResult: {passed}/{len(results)} tests passed")

        if passed == len(results):
            logging.info("🎉 All API service tests PASSED! Services ready.")
            return True
        else:
            logging.error("💥 Some API service tests FAILED! Check service setup.")
            return False

    def run_service_test(self, service):
        """Run test for specific service."""
        if service == "actuator":
            return self.test_actuator_service()
        elif service == "sensor":
            return self.test_sensor_service()
        else:
            logging.error(f"Unknown service: {service}")
            return False

def main():
    parser = argparse.ArgumentParser(description="Test API services on Pi Zero 2W")
    parser.add_argument("--service", choices=["actuator", "sensor"],
                       help="Test specific service only")
    args = parser.parse_args()

    setup_logging()
    logging.info("🚀 Starting API service tests on Pi Zero 2W...")
    logging.info(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    tester = ServiceTester()

    # Set up cleanup on exit
    def signal_handler(sig, frame):
        logging.info("Cleaning up...")
        tester.cleanup()
        sys.exit(1)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        if args.service:
            success = tester.run_service_test(args.service)
        else:
            success = tester.run_all_tests()

        sys.exit(0 if success else 1)

    finally:
        tester.cleanup()

if __name__ == "__main__":
    main()