# current.py
#!/usr/bin/env python3
"""
current.py
Module to handle INA219-based current sensing (DFRobot SEN0291).
Provides raw shunt counts, converted current, and built-in current register readings.
"""

import smbus2

class CurrentSensor:
    def __init__(self, address=0x45, busnum=1, r_shunt=0.1, i_max=3.0):
        """
        address : I2C address of INA219
        busnum  : I2C bus number on the Pi
        r_shunt : shunt resistor value in ohms
        i_max   : full-scale current range in amps for calibration
        """
        self.address = address
        self.bus = smbus2.SMBus(busnum)
        self.r_shunt = r_shunt

        # For raw-shunt voltage conversions: 10 µV per bit
        self.shunt_lsb_v = 10e-6
        self.shunt_current_lsb = self.shunt_lsb_v / self.r_shunt

        # Setup INA219 calibration for direct current register use
        self.current_lsb = i_max / (2 ** 15)
        cal = int(0.04096 / (self.current_lsb * self.r_shunt))
        msb = (cal >> 8) & 0xFF
        lsb = cal & 0xFF
        # Write calibration to register 0x05
        self.bus.write_i2c_block_data(self.address, 0x05, [msb, lsb])
        # Read back for verification
        data = self.bus.read_i2c_block_data(self.address, 0x05, 2)
        self.cal_value_read = lambda: (data[0] << 8) | data[1]

    def read_raw_shunt(self):
        """
        Read signed raw shunt-voltage counts (register 0x01).
        Returns signed int (counts), where 1 count = 10 µV.
        """
        data = self.bus.read_i2c_block_data(self.address, 0x01, 2)
        raw = (data[0] << 8) | data[1]
        if raw & 0x8000:
            raw -= 1 << 16
        return raw

    def read_current_shunt(self):
        """
        Convert raw shunt counts to amperes using shunt_current_lsb.
        Returns float in A.
        """
        raw = self.read_raw_shunt()
        return raw * self.shunt_current_lsb

    def read_current_reg(self):
        """
        Read the INA219 built-in current register (0x04) and return float in A.
        Uses calibration loaded in __init__.
        """
        data = self.bus.read_i2c_block_data(self.address, 0x04, 2)
        raw = (data[0] << 8) | data[1]
        if raw & 0x8000:
            raw -= 1 << 16
        return raw * self.current_lsb

    def close(self):
        """Close the I2C bus."""
        self.bus.close()