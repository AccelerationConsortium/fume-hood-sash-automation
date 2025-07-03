#!/usr/bin/env python3
"""
Tests for the HallArray class from switches.py.
"""

import sys
import os
import pytest
from unittest.mock import patch

# Add project root to Python path to allow importing from src
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


@patch('hood_sash_automation.actuator.switches.GPIO')
def test_hall_array_snapshot(mock_gpio):
    """
    Tests that the HallArray.snapshot() method correctly calls the underlying
    GPIO.input() for each pin.
    """
    from hood_sash_automation.actuator.switches import HallArray

    # Arrange
    hall_pins = [5, 6, 13, 19, 26]

    # Configure the mock to return different values for different pins
    def gpio_input_side_effect(pin):
        if pin == 13:
            return 0  # Active LOW (sensor triggered)
        return 1      # Inactive HIGH (sensor not triggered)

    # Apply the side effect to the mock
    mock_gpio.input.side_effect = gpio_input_side_effect

    # Act
    hall = HallArray(hall_pins)
    states = hall.snapshot()
    hall.close() # Teardown

    # Assert
    assert states == [1, 1, 0, 1, 1]
    mock_gpio.cleanup.assert_called_once_with(hall_pins)
