# tests/test_actuator_controller.py
import pytest

# A sample config dictionary for testing
SAMPLE_CONFIG = {
    'HALL_PINS': [5, 6, 13, 19, 26], 'BOUNCE_MS': 10, 'RELAY_EXT': 27, 'RELAY_RET': 17,
    'I2C_BUS': 1, 'INA_ADDR': 0x45, 'R_SHUNT': 0.1, 'I_MAX': 3.0,
    'CURRENT_THRESHOLD_UP': 1300, 'CURRENT_THRESHOLD_DOWN': -1300,
    'MAX_MOVEMENT_TIME': 10.0, 'POSITION_TIMEOUT': 2.0,
    'POSITION_STATE_FILE': "/tmp/test_pos", 'LOG_DIR': "/tmp/test_log"
}

@pytest.fixture
def mock_hardware(mocker):
    """This fixture creates mocks for all hardware interaction classes."""
    mocker.patch('hood_sash_automation.actuator.controller.ActuatorRelay')

    mock_cs_class = mocker.patch('hood_sash_automation.actuator.controller.CurrentSensor')
    # Configure the instance that will be created by the class mock
    mock_cs_instance = mock_cs_class.return_value
    mock_cs_instance.cal_value_read.return_value = 4096 # Return a simple int
    mock_cs_instance.read_raw_shunt.return_value = 0 # Simulate normal current

    mocker.patch('hood_sash_automation.actuator.controller.HallArray')
    mocker.patch('hood_sash_automation.actuator.controller.DFRobotLCD')
    mocker.patch('os.makedirs')
    mocker.patch('hood_sash_automation.actuator.controller.SashActuator._setup_logging')
    mocker.patch('hood_sash_automation.actuator.controller.SashActuator._write_position_state')


def test_sash_actuator_initialization(mock_hardware):
    """Test that the SashActuator initializes its components."""
    from hood_sash_automation.actuator.controller import SashActuator, ActuatorRelay, HallArray

    SashActuator.home_on_startup = lambda self: None
    actuator = SashActuator(SAMPLE_CONFIG)

    HallArray.assert_called_once_with(SAMPLE_CONFIG['HALL_PINS'], bouncetime=SAMPLE_CONFIG['BOUNCE_MS'])
    ActuatorRelay.assert_called_once_with(SAMPLE_CONFIG['RELAY_EXT'], SAMPLE_CONFIG['RELAY_RET'])

    mock_hall_instance = HallArray.return_value
    mock_hall_instance.set_callback.assert_called_once_with(actuator.hall_callback)


def test_move_up_command(mock_hardware, mocker):
    """Test the logic for a simple 'move up' command."""
    from hood_sash_automation.actuator.controller import SashActuator, ActuatorRelay, HallArray

    mocker.patch('threading.Thread.start')
    mock_hall_instance = HallArray.return_value
    mock_hall_instance.snapshot.return_value = [0, 1, 1, 1, 1]

    SashActuator.home_on_startup = lambda self: None
    actuator = SashActuator(SAMPLE_CONFIG)

    actuator.move_to_position_async(3)

    mock_relay_instance = ActuatorRelay.return_value
    assert actuator.movement_thread._target == actuator.move_to_position

    actuator.move_to_position(target_pos=3, mode='position')

    mock_relay_instance.up_on.assert_called_once()
    mock_relay_instance.down_on.assert_not_called()
