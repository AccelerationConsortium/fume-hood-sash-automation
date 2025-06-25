# tests/test_actuator_api.py
import pytest
from unittest.mock import patch
import os

# This fixture is automatically used by pytest for tests in this file.
# It patches the SashActuator class *before* it's imported by the api_service.
@pytest.fixture(autouse=True)
def mock_actuator_class(mocker):
    """Mocks the SashActuator class."""
    mock = mocker.patch('hood_sash_automation.actuator.api_service.SashActuator')
    # The mock will be used to instantiate the `actuator` global in api_service
    yield mock

@pytest.fixture(name="client_and_mock")
def client_fixture(mock_actuator_class):
    """
    Creates a Flask test client and provides the mock instance of the actuator
    that the app is using.
    """
    os.environ['FLASK_ENV'] = 'testing'
    from hood_sash_automation.actuator.api_service import create_app
    app = create_app()
    # The `actuator` instance in the app is now the instance created from our mock class
    mock_instance = app.actuator
    with app.test_client() as client:
        yield client, mock_instance

def test_status_endpoint_returns_mocked_status(client_and_mock):
    """Test the /status endpoint."""
    client, mock_actuator = client_and_mock
    # Arrange
    mock_actuator.get_status.return_value = {"position": 3, "moving": False}

    # Act
    response = client.get('/status')

    # Assert
    assert response.status_code == 200
    assert response.json == {"position": 3, "moving": False}
    mock_actuator.get_status.assert_called_once()

def test_move_endpoint_success(client_and_mock):
    """Test the /move endpoint for a successful request."""
    client, mock_actuator = client_and_mock
    # Arrange
    mock_actuator.move_to_position_async.return_value = True
    
    # Act
    response = client.post('/move', json={'position': 4})
    
    # Assert
    assert response.status_code == 202
    assert response.get_json() == {"message": "Moving to position 4"}
    mock_actuator.move_to_position_async.assert_called_with(4)

def test_move_endpoint_invalid_position(client_and_mock):
    """Test the /move endpoint with an out-of-range position."""
    client, mock_actuator = client_and_mock
    # Act
    response = client.post('/move', json={'position': 99})

    # Assert
    assert response.status_code == 400
    assert "Invalid position" in response.get_json()['error']

def test_move_endpoint_actuator_busy(client_and_mock):
    """Test the /move endpoint when the actuator is busy."""
    client, mock_actuator = client_and_mock
    # Arrange
    mock_actuator.move_to_position_async.return_value = False

    # Act
    response = client.post('/move', json={'position': 4})
    
    # Assert
    assert response.status_code == 409
    assert "already moving" in response.get_json()['message']

def test_stop_endpoint(client_and_mock):
    """Test the /stop endpoint."""
    client, mock_actuator = client_and_mock
    # Act
    response = client.post('/stop')

    # Assert
    assert response.status_code == 200
    assert response.json == {'message': 'Stop command issued.'}
    mock_actuator.stop.assert_called_once() 