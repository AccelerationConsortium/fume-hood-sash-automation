# tests/test_integration_actuator.py - Integration testing with minimal mocking
import pytest
import os
from unittest.mock import patch, MagicMock

# Sample config for integration testing
INTEGRATION_CONFIG = {
    'HALL_PINS': [5, 6, 13, 19, 26], 'BOUNCE_MS': 10, 'RELAY_EXT': 27, 'RELAY_RET': 17,
    'I2C_BUS': 1, 'INA_ADDR': 0x45, 'R_SHUNT': 0.1, 'I_MAX': 3.0,
    'CURRENT_THRESHOLD_UP': 1300, 'CURRENT_THRESHOLD_DOWN': -1300,
    'MAX_MOVEMENT_TIME': 10.0, 'POSITION_TIMEOUT': 2.0,
    'POSITION_STATE_FILE': "/tmp/test_pos", 'LOG_DIR': "/tmp/test_log"
}

@pytest.fixture
def minimal_hardware_mock(mocker):
    """Minimal hardware mocking - only mock the hardware interfaces, not the classes."""
    # Mock GPIO at all import locations so the real classes can use our mock
    import hood_sash_automation.actuator.relay
    import hood_sash_automation.actuator.hall
    mock_gpio = mocker.patch.object(hood_sash_automation.actuator.relay, 'GPIO')
    mocker.patch.object(hood_sash_automation.actuator.hall, 'GPIO', mock_gpio)

    mock_gpio.HIGH = 1
    mock_gpio.LOW = 0
    mock_gpio.OUT = 'out'
    mock_gpio.IN = 'in'
    mock_gpio.PUD_UP = 'pud_up'
    mock_gpio.BOTH = 'both'
    mock_gpio.input.return_value = 1  # Default: all sensors inactive

    # Mock current sensor I2C operations only
    mock_smbus = mocker.patch('hood_sash_automation.actuator.current.smbus2.SMBus')
    mock_smbus_instance = MagicMock()
    mock_smbus_instance.read_i2c_block_data.return_value = [0x11, 0x79]  # Return valid calibration
    mock_smbus.return_value = mock_smbus_instance

    # Mock LCD display only
    mock_lcd = mocker.patch('hood_sash_automation.actuator.controller.DFRobotLCD')
    mock_lcd_instance = MagicMock()
    mock_lcd.return_value = mock_lcd_instance

    # Mock file operations
    mocker.patch('os.makedirs')
    mock_open = mocker.patch('builtins.open', mocker.mock_open())

    return mock_gpio, mock_open

class TestActuatorIntegration:
    """Integration tests with actual component interactions."""

    def test_actuator_initialization_sequence(self, minimal_hardware_mock):
        """Test that actuator initializes all components in correct order."""
        mock_gpio, mock_open = minimal_hardware_mock

        from hood_sash_automation.actuator.controller import SashActuator

        # Override home_on_startup to avoid complex initialization
        with patch.object(SashActuator, 'home_on_startup'):
            actuator = SashActuator(INTEGRATION_CONFIG)

        # Verify components are properly initialized (this is the real integration test)
        assert actuator.hall is not None
        assert actuator.relay is not None
        assert actuator.sensor is not None

        # Verify that GPIO was used (even if our mock doesn't see all calls due to imports)
        assert mock_gpio.setup.called
        assert mock_gpio.setmode.called

    def test_position_state_persistence(self, minimal_hardware_mock):
        """Test that position state is properly saved and loaded."""
        mock_gpio, mock_open = minimal_hardware_mock

        from hood_sash_automation.actuator.controller import SashActuator

        with patch.object(SashActuator, 'home_on_startup'):
            actuator = SashActuator(INTEGRATION_CONFIG)

        # Test position state writing (method takes no position parameter)
        actuator.current_position = 3
        actuator._write_position_state()

        # Verify file was opened for writing
        mock_open.assert_called_with(INTEGRATION_CONFIG['POSITION_STATE_FILE'], 'w')
        handle = mock_open.return_value
        handle.write.assert_called_with('3')

    def test_hall_sensor_position_detection(self, minimal_hardware_mock):
        """Test position detection logic works correctly."""
        mock_gpio, mock_open = minimal_hardware_mock

        from hood_sash_automation.actuator.controller import SashActuator

        with patch.object(SashActuator, 'home_on_startup'):
            actuator = SashActuator(INTEGRATION_CONFIG)

        # Test the position detection logic by directly testing the method
        # Since GPIO mocking is complex, test the logic directly

        # Mock the hall.snapshot method to return specific states
        with patch.object(actuator.hall, 'snapshot', return_value=[1, 1, 0, 1, 1]):
            position = actuator.get_current_position()
            assert position == 3  # Should detect position 3 (index 2 + 1)

        # Test another position
        with patch.object(actuator.hall, 'snapshot', return_value=[0, 1, 1, 1, 1]):
            position = actuator.get_current_position()
            assert position == 1  # Should detect position 1 (index 0 + 1)

        # Test no position detected
        with patch.object(actuator.hall, 'snapshot', return_value=[1, 1, 1, 1, 1]):
            position = actuator.get_current_position()
            assert position is None  # No sensors active

    def test_relay_control_integration(self, minimal_hardware_mock):
        """Test relay control through the actuator."""
        mock_gpio, mock_open = minimal_hardware_mock

        from hood_sash_automation.actuator.controller import SashActuator

        with patch.object(SashActuator, 'home_on_startup'):
            actuator = SashActuator(INTEGRATION_CONFIG)

        # Test relay control through actuator
        actuator.relay.up_on()

        # Verify correct GPIO calls
        mock_gpio.output.assert_any_call(INTEGRATION_CONFIG['RELAY_EXT'], mock_gpio.HIGH)
        mock_gpio.output.assert_any_call(INTEGRATION_CONFIG['RELAY_RET'], mock_gpio.LOW)

    def test_current_monitoring_integration(self, minimal_hardware_mock):
        """Test current monitoring integration."""
        mock_gpio, mock_open = minimal_hardware_mock

        from hood_sash_automation.actuator.controller import SashActuator

        with patch.object(SashActuator, 'home_on_startup'):
            actuator = SashActuator(INTEGRATION_CONFIG)

        # Mock current sensor to return high current by patching the method
        with patch.object(actuator.sensor, 'read_raw_shunt', return_value=2000):
        # Test current monitoring
            is_safe = actuator._check_movement_current('up')
            assert is_safe == False  # Should return False when overcurrent detected

class TestAPIIntegration:
    """Integration tests for the API with actual Flask app."""

    @pytest.fixture
    def app_with_minimal_mocking(self, minimal_hardware_mock):
        """Create Flask app with minimal hardware mocking."""
        os.environ['FLASK_ENV'] = 'testing'

        # Mock the config loading to return our test config
        mock_config = {
            'hall_pins': [5, 6, 13, 19, 26], 'bounce_ms': 10, 'relay_ext_pin': 27, 'relay_ret_pin': 17,
            'i2c_bus': 1, 'ina_addr': 0x45, 'r_shunt': 0.1, 'i_max': 3.0,
            'current_threshold_up': 1300, 'current_threshold_down': -1300,
            'max_movement_time': 10.0, 'position_timeout': 2.0,
            'position_state_file': "/tmp/test_pos", 'log_dir': "/tmp/test_log"
        }

        with patch('hood_sash_automation.actuator.api_service.SashActuator') as mock_actuator_class:
            # Configure the mock actuator instance
            mock_instance = MagicMock()
            mock_instance.get_status.return_value = {"position": 2, "moving": False}
            mock_actuator_class.return_value = mock_instance

            with patch('yaml.safe_load', return_value=mock_config):
            from hood_sash_automation.actuator.api_service import create_app
            app = create_app()

            with app.test_client() as client:
                yield client, mock_instance

    def test_api_error_handling_integration(self, app_with_minimal_mocking):
        """Test API error handling with real Flask context."""
        client, mock_actuator = app_with_minimal_mocking

        # Simulate actuator exception
        mock_actuator.get_status.side_effect = Exception("Hardware error")

        response = client.get('/status')

        # Should handle exception gracefully
        assert response.status_code == 500
        # Flask default error response might not be JSON, so check content type
        if response.content_type == 'application/json':
        data = response.get_json()
        assert 'error' in data
        else:
            # Check that an error response was returned
            assert b'error' in response.data.lower() or b'internal server error' in response.data.lower()

    def test_api_request_validation_integration(self, app_with_minimal_mocking):
        """Test comprehensive request validation."""
        client, mock_actuator = app_with_minimal_mocking

        # Test various invalid requests
        test_cases = [
            ({'position': 'invalid'}, 400),  # Non-numeric position
            ({'position': -1}, 400),         # Negative position
            ({'position': 10}, 400),         # Out of range position
            ({'wrong_key': 3}, 400),         # Missing position key
        ]

        for payload, expected_status in test_cases:
            response = client.post('/move', json=payload)
            assert response.status_code == expected_status