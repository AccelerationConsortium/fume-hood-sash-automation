#!/usr/bin/env python3
"""
SSH Client Example for Fume Hood Sash Automation
Demonstrates remote control via SSH with proper error handling.
"""

import subprocess
import json
import time
import sys

class FumeHoodSSHClient:
    def __init__(self, pi_ip, username='pi'):
        self.pi_ip = pi_ip
        self.username = username
        self.base_url = "http://localhost:5000"
    
    def _ssh_command(self, command):
        """Execute a command via SSH and return the result."""
        try:
            result = subprocess.run(
                ['ssh', f'{self.username}@{self.pi_ip}', command],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                raise Exception(f"SSH command failed: {result.stderr}")
                
            return result.stdout.strip()
        except subprocess.TimeoutExpired:
            raise Exception("SSH command timed out")
        except Exception as e:
            raise Exception(f"SSH error: {e}")
    
    def _api_call(self, endpoint, method='GET', data=None):
        """Make an API call via SSH."""
        if method == 'GET':
            command = f"curl -s {self.base_url}{endpoint}"
        elif method == 'POST':
            if data:
                json_data = json.dumps(data).replace('"', '\\"')
                command = f"curl -X POST {self.base_url}{endpoint} -H 'Content-Type: application/json' -d \"{json_data}\""
            else:
                command = f"curl -X POST {self.base_url}{endpoint}"
        
        response = self._ssh_command(command)
        
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            raise Exception(f"Invalid JSON response: {response}")
    
    def get_status(self):
        """Get current system status."""
        return self._api_call('/status')
    
    def get_position(self):
        """Get current position only."""
        return self._api_call('/position')
    
    def move_to_position(self, position):
        """Move to specified position (1-5)."""
        if not isinstance(position, int) or not 1 <= position <= 5:
            raise ValueError("Position must be an integer between 1 and 5")
        
        return self._api_call('/move', 'POST', {'position': position})
    
    def stop(self):
        """Emergency stop."""
        return self._api_call('/stop', 'POST')
    
    def wait_for_movement_complete(self, timeout=30):
        """Wait for current movement to complete."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                status = self.get_status()
                if not status.get('is_moving', False):
                    return True
                    
                print(f"Still moving... position: {status.get('current_position', 'unknown')}")
                time.sleep(1)
                
            except Exception as e:
                print(f"Error checking status: {e}")
                time.sleep(1)
        
        raise Exception(f"Movement did not complete within {timeout} seconds")
    
    def move_and_wait(self, position, timeout=30):
        """Move to position and wait for completion."""
        print(f"🚀 Moving to position {position}...")
        response = self.move_to_position(position)
        
        if 'error' in response:
            raise Exception(f"Move failed: {response['error']}")
        
        print(f"✅ Move command accepted: {response.get('message', '')}")
        
        if self.wait_for_movement_complete(timeout):
            final_status = self.get_status()
            print(f"🎯 Movement complete! Position: {final_status.get('current_position')}")
            return final_status
    
    def get_service_logs(self, lines=20):
        """Get recent service logs."""
        command = f"journalctl -u actuator.service -n {lines} --no-pager"
        return self._ssh_command(command)
    
    def restart_service(self):
        """Restart the actuator service."""
        command = "sudo systemctl restart actuator.service"
        return self._ssh_command(command)
    
    def check_service_status(self):
        """Check if the service is running."""
        command = "systemctl is-active actuator.service"
        try:
            result = self._ssh_command(command)
            return result.strip() == 'active'
        except:
            return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python ssh_client_example.py <pi-ip> [command] [args...]")
        print("\nExamples:")
        print("  python ssh_client_example.py 192.168.1.100 status")
        print("  python ssh_client_example.py 192.168.1.100 move 3")
        print("  python ssh_client_example.py 192.168.1.100 sequence")
        sys.exit(1)
    
    pi_ip = sys.argv[1]
    command = sys.argv[2] if len(sys.argv) > 2 else 'status'
    
    try:
        client = FumeHoodSSHClient(pi_ip)
        
        if command == 'status':
            status = client.get_status()
            print(f"📊 Status: {json.dumps(status, indent=2)}")
            
        elif command == 'position':
            pos = client.get_position()
            print(f"📍 Position: {json.dumps(pos, indent=2)}")
            
        elif command == 'move':
            if len(sys.argv) < 4:
                print("Error: Position required for move command")
                sys.exit(1)
            position = int(sys.argv[3])
            client.move_and_wait(position)
            
        elif command == 'stop':
            response = client.stop()
            print(f"🛑 Stop: {json.dumps(response, indent=2)}")
            
        elif command == 'logs':
            logs = client.get_service_logs()
            print("📋 Recent logs:")
            print(logs)
            
        elif command == 'sequence':
            # Demo sequence: move through positions
            print("🎭 Running demo sequence...")
            for pos in [1, 3, 5, 2, 1]:
                client.move_and_wait(pos, timeout=15)
                time.sleep(2)
            print("✅ Sequence complete!")
            
        else:
            print(f"Unknown command: {command}")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main() 