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
    # Mock the classes themselves
    mocker.patch('src.hood_sash_automation.actuator.controller.ActuatorRelay')
    mocker.patch('src.hood_sash_automation.actuator.controller.CurrentSensor')
    mocker.patch('src.hood_sash_automation.actuator.controller.HallArray')
    mocker.patch('src.hood_sash_automation.actuator.controller.DFRobotLCD')
    # We need to also mock the os.makedirs call during logging setup
    mocker.patch('os.makedirs')


def test_sash_actuator_initialization(mock_hardware):
    """Test that the SashActuator initializes its components."""
    from src.hood_sash_automation.actuator.controller import SashActuator, ActuatorRelay, HallArray
    
    # We have to disable the auto-homing for this simple test
    SashActuator.home_on_startup = lambda self: None

    actuator = SashActuator(SAMPLE_CONFIG)

    # Assert that the hardware classes were instantiated
    HallArray.assert_called_once_with(SAMPLE_CONFIG['HALL_PINS'], bouncetime=SAMPLE_CONFIG['BOUNCE_MS'])
    ActuatorRelay.assert_called_once_with(SAMPLE_CONFIG['RELAY_EXT'], SAMPLE_CONFIG['RELAY_RET'])
    
    # Assert that the hall callback was set
    mock_hall_instance = HallArray.return_value
    mock_hall_instance.set_callback.assert_called_once_with(actuator.hall_callback)


def test_move_up_command(mock_hardware, mocker):
    """Test the logic for a simple 'move up' command."""
    from src.hood_sash_automation.actuator.controller import SashActuator, ActuatorRelay, HallArray
    
    # Arrange
    # Prevent the movement thread from starting and blocking the test
    mocker.patch('threading.Thread.start')

    # Configure the mock HallArray to report being at position 1
    mock_hall_instance = HallArray.return_value
    mock_hall_instance.snapshot.return_value = [0, 1, 1, 1, 1] # 0 means magnet present at index 0 (pos 1)
    
    SashActuator.home_on_startup = lambda self: None
    actuator = SashActuator(SAMPLE_CONFIG)
    
    # Act
    actuator.move_to_position_async(3) # Command a move from 1 to 3

    # Assert
    # Check that the movement thread was created with the right target
    mock_relay_instance = ActuatorRelay.return_value
    assert actuator.movement_thread.target == actuator.move_to_position
    
    # To test the logic inside the thread, we can call the target method directly
    actuator.move_to_position(target_pos=3, mode='position')
    
    # Assert that the 'up' relay was turned on
    mock_relay_instance.up_on.assert_called_once()
    mock_relay_instance.down_on.assert_not_called()
     