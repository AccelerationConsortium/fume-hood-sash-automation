#!/usr/bin/env python3
"""
Fume Hood Sash Microservice Client
For integration into external UI applications.

Usage:
    from microservice_client import FumeHoodSashClient

    client = FumeHoodSashClient('192.168.1.100')
    status = client.get_status()
    client.move_to_position(3)
"""

import subprocess
import json
import time
from typing import Dict, Optional, Union

class FumeHoodSashClient:
    """
    Client for controlling Fume Hood Sash microservice via SSH.

    This class provides a clean interface for your UI application
    to control the fume hood sash remotely.
    """

    def __init__(self, pi_ip: str, username: str = 'pi', port: int = 5000):
        """
        Initialize the client.

        Args:
            pi_ip: IP address of the Raspberry Pi
            username: SSH username (default: 'pi')
            port: API port on the Pi (default: 5000)
        """
        self.pi_ip = pi_ip
        self.username = username
        self.port = port
        self.base_url = f"http://localhost:{port}"

    def _ssh_request(self, endpoint: str, method: str = 'GET', data: Optional[Dict] = None) -> Dict:
        """
        Execute HTTP request via SSH.

        Args:
            endpoint: API endpoint (e.g., '/status')
            method: HTTP method ('GET' or 'POST')
            data: JSON data for POST requests

        Returns:
            Dict: JSON response from the API

        Raises:
            Exception: On SSH or API errors
        """
        if method == 'GET':
            curl_cmd = f"curl -s {self.base_url}{endpoint}"
        elif method == 'POST':
            if data:
                json_data = json.dumps(data).replace('"', '\\"')
                curl_cmd = f'curl -X POST {self.base_url}{endpoint} -H "Content-Type: application/json" -d "{json_data}"'
            else:
                curl_cmd = f"curl -X POST {self.base_url}{endpoint}"
        else:
            raise ValueError(f"Unsupported method: {method}")

        try:
            result = subprocess.run(
                ['ssh', f'{self.username}@{self.pi_ip}', curl_cmd],
                capture_output=True,
                text=True,
                timeout=15
            )

            if result.returncode != 0:
                raise Exception(f"SSH command failed: {result.stderr.strip()}")

            response_text = result.stdout.strip()
            if not response_text:
                raise Exception("Empty response from API")

            return json.loads(response_text)

        except subprocess.TimeoutExpired:
            raise Exception("Request timed out")
        except json.JSONDecodeError as e:
            raise Exception(f"Invalid JSON response: {response_text}")
        except Exception as e:
            raise Exception(f"Request failed: {str(e)}")

    def get_status(self) -> Dict[str, Union[int, bool]]:
        """
        Get complete system status.

        Returns:
            Dict with keys:
            - current_position: int (1-5 or None)
            - is_moving: bool
        """
        return self._ssh_request('/status')

    def get_position(self) -> Optional[int]:
        """
        Get current sash position only.

        Returns:
            int: Current position (1-5) or None if unknown
        """
        response = self._ssh_request('/position')
        return response.get('position')

    def move_to_position(self, position: int) -> Dict[str, str]:
        """
        Move sash to specified position.

        Args:
            position: Target position (1-5)

        Returns:
            Dict with 'message' key on success, 'error' key on failure

        Raises:
            ValueError: If position is invalid
            Exception: On communication or API errors
        """
        if not isinstance(position, int) or not (1 <= position <= 5):
            raise ValueError("Position must be an integer between 1 and 5")

        return self._ssh_request('/move', 'POST', {'position': position})

    def stop(self) -> Dict[str, str]:
        """
        Issue emergency stop command.

        Returns:
            Dict with 'message' key
        """
        return self._ssh_request('/stop', 'POST')

    def is_moving(self) -> bool:
        """
        Check if sash is currently moving.

        Returns:
            bool: True if moving, False if stationary
        """
        status = self.get_status()
        return status.get('is_moving', False)

    def wait_for_movement_complete(self, timeout: int = 30, poll_interval: float = 1.0) -> bool:
        """
        Wait for current movement to complete.

        Args:
            timeout: Maximum time to wait in seconds
            poll_interval: How often to check status in seconds

        Returns:
            bool: True if movement completed, False if timed out
        """
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                if not self.is_moving():
                    return True
                time.sleep(poll_interval)
            except Exception:
                # Continue polling even if individual requests fail
                time.sleep(poll_interval)

        return False

    def move_and_wait(self, position: int, timeout: int = 30) -> Dict[str, Union[int, bool]]:
        """
        Move to position and wait for completion.

        Args:
            position: Target position (1-5)
            timeout: Maximum time to wait for completion

        Returns:
            Dict: Final status after movement

        Raises:
            ValueError: If position is invalid
            Exception: On movement failure or timeout
        """
        # Initiate movement
        response = self.move_to_position(position)

        if 'error' in response:
            raise Exception(f"Move command failed: {response['error']}")

        # Wait for completion
        if not self.wait_for_movement_complete(timeout):
            raise Exception(f"Movement did not complete within {timeout} seconds")

        return self.get_status()

    def ping(self) -> bool:
        """
        Test if the microservice is reachable and responding.

        Returns:
            bool: True if service is reachable
        """
        try:
            self.get_status()
            return True
        except:
            return False


# Example usage for testing
if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print("Usage: python microservice_client.py <pi_ip>")
        sys.exit(1)

    pi_ip = sys.argv[1]
    client = FumeHoodSashClient(pi_ip)

    try:
        # Test connection
        print("🔍 Testing connection...")
        if not client.ping():
            print("❌ Cannot reach microservice")
            sys.exit(1)
        print("✅ Connection OK")

        # Get current status
        print("\n📊 Current Status:")
        status = client.get_status()
        print(f"  Position: {status.get('current_position', 'Unknown')}")
        print(f"  Moving: {status.get('is_moving', False)}")

        # Demo movement (uncomment to test)
        # print("\n🚀 Testing movement to position 3...")
        # final_status = client.move_and_wait(3)
        # print(f"✅ Movement complete: {final_status}")

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)