#!/usr/bin/env python3
"""
Tests for the HallArray event callback functionality.
"""
import os
import sys
from unittest.mock import MagicMock, patch

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


@patch('hood_sash_automation.actuator.switches.threading.Thread')
@patch('hood_sash_automation.actuator.switches.GPIO')
def test_hall_event_callback(mock_gpio, mock_thread):
    """Tests that the HallArray callback fires when a polled pin changes."""
    from hood_sash_automation.actuator.switches import HallArray

    # Arrange
    hall_pins = [5, 6, 13, 19, 26]
    callback_func = MagicMock()  # A mock to act as our callback

    mock_gpio.input.return_value = 1
    hall = HallArray(hall_pins, bouncetime=10)
    hall.set_callback(callback_func)

    # Configure the mock GPIO to report that the pin is now active (LOW)
    mock_gpio.input.return_value = 0

    # Act: use the compatibility hook to simulate a GPIO state change.
    hall._isr(channel=13)

    # Assert:
    # Check that our registered callback function was called with the
    # arguments we expect for this event.
    callback_func.assert_called_once_with(13, 0, 2)

    hall.close()


@patch('hood_sash_automation.actuator.switches.threading.Thread')
@patch('hood_sash_automation.actuator.switches.GPIO')
def test_hall_poll_once_detects_changed_pin(mock_gpio, mock_thread):
    """Tests that one polling pass emits a callback for changed pins."""
    from hood_sash_automation.actuator.switches import HallArray

    hall_pins = [5, 6, 13, 19, 26]
    callback_func = MagicMock()
    initial_states = {pin: 1 for pin in hall_pins}
    changed_states = {**initial_states, 13: 0}

    mock_gpio.input.side_effect = lambda pin: initial_states[pin]
    hall = HallArray(hall_pins, bouncetime=10)
    hall.set_callback(callback_func)

    mock_gpio.input.side_effect = lambda pin: changed_states[pin]
    hall._poll_once()

    callback_func.assert_called_once_with(13, 0, 2)
    assert hall.snapshot() == [1, 1, 0, 1, 1]
    mock_thread.return_value.start.assert_called_once()
    hall.close()
