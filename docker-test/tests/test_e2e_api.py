# tests/test_e2e_api.py - End-to-end API testing
import pytest
import requests
import os
import time

ACTUATOR_URL = os.getenv('ACTUATOR_URL', 'http://localhost:5000')
SENSOR_URL = os.getenv('SENSOR_URL', 'http://localhost:5005')

@pytest.fixture(scope="module")
def wait_for_services():
    """Wait for services to be ready before running tests."""
    max_retries = 30
    retry_delay = 1
    
    for service_name, url in [("actuator", ACTUATOR_URL), ("sensor", SENSOR_URL)]:
        for i in range(max_retries):
            try:
                response = requests.get(f"{url}/status", timeout=5)
                if response.status_code == 200:
                    print(f"✓ {service_name} service is ready")
                    break
            except requests.exceptions.RequestException:
                if i == max_retries - 1:
                    pytest.fail(f"❌ {service_name} service failed to start")
                time.sleep(retry_delay)

class TestActuatorServiceE2E:
    """End-to-end tests for actuator service."""
    
    def test_actuator_status_endpoint(self, wait_for_services):
        """Test actuator status endpoint returns valid response."""
        response = requests.get(f"{ACTUATOR_URL}/status")
        assert response.status_code == 200
        
        data = response.json()
        assert 'position' in data
        assert 'moving' in data
        assert isinstance(data['position'], int)
        assert isinstance(data['moving'], bool)

    def test_actuator_move_endpoint_validation(self, wait_for_services):
        """Test actuator move endpoint input validation."""
        # Test invalid position
        response = requests.post(f"{ACTUATOR_URL}/move", json={'position': 99})
        assert response.status_code == 400
        assert 'error' in response.json()
        
        # Test missing position
        response = requests.post(f"{ACTUATOR_URL}/move", json={})
        assert response.status_code == 400

    def test_actuator_stop_endpoint(self, wait_for_services):
        """Test actuator stop endpoint."""
        response = requests.post(f"{ACTUATOR_URL}/stop")
        assert response.status_code == 200
        assert 'message' in response.json()

class TestSensorServiceE2E:
    """End-to-end tests for sensor service."""
    
    def test_sensor_status_endpoint(self, wait_for_services):
        """Test sensor status endpoint returns valid response."""
        response = requests.get(f"{SENSOR_URL}/status")
        assert response.status_code == 200
        
        # Basic validation that we get some kind of sensor data
        data = response.json()
        assert isinstance(data, dict)

class TestServiceIntegration:
    """Integration tests between services."""
    
    def test_both_services_healthy(self, wait_for_services):
        """Test that both services are running and responsive."""
        actuator_response = requests.get(f"{ACTUATOR_URL}/status")
        sensor_response = requests.get(f"{SENSOR_URL}/status")
        
        assert actuator_response.status_code == 200
        assert sensor_response.status_code == 200
        
        # Services should respond within reasonable time
        assert actuator_response.elapsed.total_seconds() < 2
        assert sensor_response.elapsed.total_seconds() < 2

    def test_concurrent_requests(self, wait_for_services):
        """Test services can handle concurrent requests."""
        import concurrent.futures
        import threading
        
        def make_request(url):
            return requests.get(f"{url}/status")
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = []
            
            # Make concurrent requests to both services
            for _ in range(5):
                futures.append(executor.submit(make_request, ACTUATOR_URL))
                futures.append(executor.submit(make_request, SENSOR_URL))
            
            # All requests should succeed
            for future in concurrent.futures.as_completed(futures):
                response = future.result()
                assert response.status_code == 200 