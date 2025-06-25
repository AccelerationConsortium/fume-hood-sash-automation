# tests/test_actuator_api.py
import pytest
from unittest.mock import MagicMock

# This is the key: we patch the real SashActuator class before it's imported by the api_service
from unittest.mock import patch
with patch('src.hood_sash_automation.actuator.controller.SashActuator') as mock_actuator_class:
    # We configure the mock class to return a mock instance
    mock_actuator_instance = MagicMock()
    mock_actuator_class.return_value = mock_actuator_instance
    
    # Now we can import the app. The SashActuator it uses will be our mock.
    from src.hood_sash_automation.actuator.api_service import app

@pytest.fixture
def client():
    """Create and configure a new app instance for each test."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_status_endpoint_returns_mocked_status(client):
    """
    Test the /status endpoint.
    It should return the status provided by our mock actuator instance.
    """
    # Arrange: Configure our mock actuator to return a specific status
    expected_status = {"current_position": 3, "is_moving": False}
    mock_actuator_instance.get_status.return_value = expected_status

    # Act: Make a request to the API
    response = client.get('/status')

    # Assert: Check if the response is correct
    assert response.status_code == 200
    assert response.get_json() == expected_status
    # Verify that the API called our mock's get_status method
    mock_actuator_instance.get_status.assert_called_once()

def test_move_endpoint_success(client):
    """Test the /move endpoint for a successful request."""
    # Arrange
    mock_actuator_instance.move_to_position_async.return_value = True
    
    # Act
    response = client.post('/move', json={'position': 4})
    
    # Assert
    assert response.status_code == 202
    assert response.get_json() == {"message": "Moving to position 4"}
    mock_actuator_instance.move_to_position_async.assert_called_with(4)

def test_move_endpoint_invalid_position(client):
    """Test the /move endpoint with an out-of-range position."""
    # Act
    response = client.post('/move', json={'position': 99})
    
    # Assert
    assert response.status_code == 400
    assert "Invalid position" in response.get_json()['error'] 