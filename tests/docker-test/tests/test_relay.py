# tests/test_relay.py
import pytest
from unittest.mock import patch

@patch('hood_sash_automation.actuator.relay.GPIO')
def test_relay_cycles(mock_gpio):
    """
    Tests that the relay class calls the correct GPIO functions in sequence.
    """
    from hood_sash_automation.actuator.relay import ActuatorRelay
    
    # Arrange
    UP_PIN = 17
    DOWN_PIN = 27
    relay = ActuatorRelay(up_pin=UP_PIN, down_pin=DOWN_PIN)

    # Act & Assert
    relay.up_on()
    mock_gpio.output.assert_any_call(UP_PIN, mock_gpio.HIGH)
    mock_gpio.output.assert_any_call(DOWN_PIN, mock_gpio.LOW)

    relay.down_on()
    mock_gpio.output.assert_any_call(UP_PIN, mock_gpio.LOW)
    mock_gpio.output.assert_any_call(DOWN_PIN, mock_gpio.HIGH)

    relay.all_off()
    mock_gpio.output.assert_any_call(UP_PIN, mock_gpio.LOW)
    mock_gpio.output.assert_any_call(DOWN_PIN, mock_gpio.LOW)

    relay.close()
    mock_gpio.cleanup.assert_called_once_with([UP_PIN, DOWN_PIN])
