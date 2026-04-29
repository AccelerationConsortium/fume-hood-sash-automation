#!/usr/bin/env python3
"""
API Service Tests for Raspberry Pi deployment.

By default this script validates already-running API services, which is the
normal systemd deployment flow. Use --start-processes only when you intentionally
want this script to start temporary Flask processes itself.

Usage:
    python tests/device-test/api_service_test.py
    python tests/device-test/api_service_test.py --service actuator
    python tests/device-test/api_service_test.py --service sensor
    python tests/device-test/api_service_test.py --start-processes
"""

import argparse
import json
import logging
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR / "src"))

ACTUATOR_URL = os.getenv("ACTUATOR_URL", "http://localhost:5000")
SENSOR_URL = os.getenv("SENSOR_URL", "http://localhost:5005")


def setup_logging():
    """Set up logging for API service tests."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [API-TEST] %(levelname)s: %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(ROOT_DIR / "tests" / "device-test" / "api_test.log"),
        ],
    )


class ServiceTester:
    """Test deployed or temporary API services on a Raspberry Pi."""

    def __init__(self, start_processes=False):
        self.start_processes = start_processes
        self.processes = {}

    def cleanup(self):
        """Clean up any temporary service processes started by this script."""
        for name, proc in self.processes.items():
            if proc and proc.poll() is None:
                logging.info(f"Stopping temporary {name} service...")
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()

    def _get_python_executable(self):
        """Get the Python executable that can import this package."""
        candidates = [sys.executable, "python3", "python"]
        for candidate in candidates:
            try:
                result = subprocess.run(
                    [candidate, "-c", "import hood_sash_automation; print('OK')"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    cwd=ROOT_DIR,
                )
                if result.returncode == 0:
                    logging.info(f"Using Python executable: {candidate}")
                    return candidate
            except Exception as exc:
                logging.debug(f"Python candidate failed ({candidate}): {exc}")

        logging.warning(f"Falling back to current Python: {sys.executable}")
        return sys.executable

    def _start_service_process(self, name, module):
        """Start a temporary service process for explicit --start-processes mode."""
        python_cmd = self._get_python_executable()
        env = os.environ.copy()
        env["FLASK_ENV"] = "testing"
        proc = subprocess.Popen(
            [python_cmd, "-m", module],
            cwd=ROOT_DIR,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        self.processes[name] = proc
        time.sleep(3)

        if proc.poll() is not None:
            stdout, stderr = proc.communicate()
            logging.error(f"{name} service failed to start")
            logging.error(f"stdout: {stdout.decode()}")
            logging.error(f"stderr: {stderr.decode()}")
            return False
        return True

    def _request_json(self, url, endpoint, timeout=5):
        with urlopen(f"{url}{endpoint}", timeout=timeout) as response:
            return json.loads(response.read().decode())

    def test_actuator_service(self):
        """Test actuator API health, status, position, and equipment endpoints."""
        logging.info("Testing actuator API...")

        if self.start_processes:
            if not self._start_service_process(
                "actuator", "hood_sash_automation.api.api_service"
            ):
                return False

        try:
            health = self._request_json(ACTUATOR_URL, "/health")
            status = self._request_json(ACTUATOR_URL, "/status")
            position = self._request_json(ACTUATOR_URL, "/position")
            equipment = self._request_json(ACTUATOR_URL, "/equipment/status")
        except (HTTPError, URLError, TimeoutError) as exc:
            logging.error(f"Actuator API request failed: {exc}")
            return False

        if health.get("status") != "healthy":
            logging.error(f"Unexpected actuator health response: {health}")
            return False
        if "current_position" not in status or "is_moving" not in status:
            logging.error(f"Unexpected actuator status response: {status}")
            return False
        if "position" not in position:
            logging.error(f"Unexpected actuator position response: {position}")
            return False
        required_equipment_fields = {
            "equipment_name",
            "equipment_status",
            "message",
            "system_state",
            "sash_position",
            "target_position",
            "sash_state",
            "is_moving",
        }
        if not required_equipment_fields.issubset(equipment):
            logging.error(f"Unexpected actuator equipment response: {equipment}")
            return False

        logging.info(f"Actuator API OK: {status}; equipment={equipment}")
        return True

    def test_sensor_service(self):
        """Test sensor API status endpoint."""
        logging.info("Testing sensor API...")

        if self.start_processes:
            if not self._start_service_process(
                "sensor", "hood_sash_automation.sensor.api_service"
            ):
                return False

        try:
            status = self._request_json(SENSOR_URL, "/status")
        except (HTTPError, URLError, TimeoutError) as exc:
            logging.error(f"Sensor API request failed: {exc}")
            return False

        if "magnet_present" not in status:
            logging.error(f"Unexpected sensor status response: {status}")
            return False

        logging.info(f"Sensor API OK: {status}")
        return True

    def run_all_tests(self):
        """Run requested API service tests."""
        tests = [
            ("Actuator Service", self.test_actuator_service),
            ("Sensor Service", self.test_sensor_service),
        ]

        results = []
        for test_name, test_func in tests:
            logging.info(f"\n{'=' * 50}")
            logging.info(f"Running: {test_name}")
            logging.info(f"{'=' * 50}")
            try:
                results.append((test_name, test_func()))
            except Exception as exc:
                logging.error(f"{test_name} crashed: {exc}")
                results.append((test_name, False))

        return self._summarize(results)

    def run_service_test(self, service):
        """Run test for a specific service."""
        if service == "actuator":
            return self._summarize([("Actuator Service", self.test_actuator_service())])
        if service == "sensor":
            return self._summarize([("Sensor Service", self.test_sensor_service())])

        logging.error(f"Unknown service: {service}")
        return False

    def _summarize(self, results):
        logging.info(f"\n{'=' * 50}")
        logging.info("API SERVICE TEST SUMMARY")
        logging.info(f"{'=' * 50}")

        passed = 0
        for test_name, result in results:
            status = "PASS" if result else "FAIL"
            logging.info(f"{status} {test_name}")
            if result:
                passed += 1

        logging.info(f"\nResult: {passed}/{len(results)} tests passed")
        return passed == len(results)


def main():
    parser = argparse.ArgumentParser(description="Test Raspberry Pi API services")
    parser.add_argument("--service", choices=["actuator", "sensor"])
    parser.add_argument(
        "--start-processes",
        action="store_true",
        help="Start temporary Flask processes instead of checking deployed services",
    )
    args = parser.parse_args()

    setup_logging()
    logging.info("Starting API service tests...")

    tester = ServiceTester(start_processes=args.start_processes)

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
