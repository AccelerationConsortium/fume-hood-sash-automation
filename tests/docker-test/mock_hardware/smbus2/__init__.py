# This file makes the 'smbus2' directory a Python package.
# We need to avoid circular import, so we'll import directly from the standalone file
import sys
import os

# Get the standalone smbus2.py file path
_mock_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'smbus2.py')

# Import the SMBus class from the standalone file
import importlib.util
spec = importlib.util.spec_from_file_location("smbus2_mock", _mock_file)
smbus2_mock = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smbus2_mock)

# Export the SMBus class
SMBus = smbus2_mock.SMBus