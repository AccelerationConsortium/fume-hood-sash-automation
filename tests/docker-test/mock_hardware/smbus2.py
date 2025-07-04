"""
A mock smbus2 library to simulate I2C communication for testing on non-Pi hardware.
"""

import logging

# --- Mock State ---
# This dictionary will store the state of all I2C devices and their registers.
# Example: _i2c_devices = {0x45: {0x01: [0x12, 0x34], 0x05: [0xAB, 0xCD]}}
_i2c_devices = {}

# --- Logging ---
logging.basicConfig(level=logging.INFO, format='[MockSMBus] %(message)s')

class SMBus:
    """A mock SMBus class that simulates I2C communication."""

    def __init__(self, busnum=None):
        """Initializes the mock I2C bus."""
        if busnum is None:
            raise ValueError("Bus number must be specified.")
        self.busnum = busnum
        logging.info(f"Mock SMBus opened on bus {self.busnum}")

    def write_i2c_block_data(self, i2c_addr, register, data):
        """Mocks writing a block of data to an I2C register."""
        if not isinstance(data, list):
            raise TypeError("Data must be a list of bytes.")

        if i2c_addr not in _i2c_devices:
            _i2c_devices[i2c_addr] = {}

        _i2c_devices[i2c_addr][register] = data
        logging.info(f"Wrote to addr=0x{i2c_addr:02X} reg=0x{register:02X} data={data}")

    def read_i2c_block_data(self, i2c_addr, register, length):
        """Mocks reading a block of data from an I2C register."""
        device = _i2c_devices.get(i2c_addr, {})
        reg_data = device.get(register, [0] * length)

        # Ensure the returned data is of the correct length
        response = (reg_data + [0] * length)[:length]
        logging.info(f"Read from addr=0x{i2c_addr:02X} reg=0x{register:02X} -> data={response}")
        return response

    def close(self):
        """Mocks closing the I2C bus."""
        logging.info(f"Mock SMBus closed on bus {self.busnum}")

# --- Helper for testing ---
def set_i2c_register(address, register, value):
    """A helper function for tests to manually set an I2C register's value."""
    if address not in _i2c_devices:
        _i2c_devices[address] = {}
    _i2c_devices[address][register] = value
    logging.info(f"Test helper set addr=0x{address:02X} reg=0x{register:02X} to {value}")

def get_i2c_register(address, register):
    """A helper to inspect an I2C register's state during tests."""
    return _i2c_devices.get(address, {}).get(register)

def clear_i2c_devices():
    """A helper to reset the I2C mock state between tests."""
    _i2c_devices.clear()