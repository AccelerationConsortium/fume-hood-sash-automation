#!/usr/bin/env python3
"""
Tests for the HallArray event callback functionality.
"""
import sys
import os
import pytest
from unittest.mock import MagicMock, patch

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


@patch('hood_sash_automation.actuator.switches.GPIO')
def test_hall_event_callback(mock_gpio):
    """
    Tests that the HallArray callback fires correctly when the underlying
    GPIO event mechanism is triggered.
    """
    from hood_sash_automation.actuator.switches import HallArray

    # Arrange
    hall_pins = [5, 6, 13, 19, 26]
    callback_func = MagicMock()  # A mock to act as our callback

    # Initialize the class we are testing
    hall = HallArray(hall_pins, bouncetime=10)
    hall.set_callback(callback_func)

    # Configure the mock GPIO to report that the pin is now active (LOW)
    mock_gpio.input.return_value = 0

    # Act:
    # Directly call the internal ISR method to simulate a hardware interrupt
    # for GPIO pin 13.
    hall._isr(channel=13)

    # Assert:
    # Check that our registered callback function was called with the
    # arguments we expect for this event.
    callback_func.assert_called_once_with(13, 0, 2)

    # Teardown
    hall.close()
