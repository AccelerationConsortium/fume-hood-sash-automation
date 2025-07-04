# users/examples/remote_control_example.py

import requests
import time
import sys

# --- Configuration ---
# IMPORTANT: Replace with the IP address or hostname of your Raspberry Pi.
PI_HOST = "raspberrypi.local"
ACTUATOR_PORT = 5000
BASE_URL = f"http://{PI_HOST}:{ACTUATOR_PORT}"

def check_service_status():
    """Checks if the actuator service is running before starting."""
    try:
        response = requests.get(f"{BASE_URL}/status", timeout=5)
        response.raise_for_status()
        print(f"Successfully connected to the actuator service at {BASE_URL}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error: Could not connect to the actuator service at {BASE_URL}.")
        print(f"Please ensure the service is running on the Pi and that the PI_HOST is correct.")
        print(f"Details: {e}")
        return False

def move_to_position(position):
    """Sends a command to move the sash to a specific position."""
    print(f"\n>>> Sending command to move to position {position}...")
    try:
        response = requests.post(f"{BASE_URL}/move", json={"position": position})
        response.raise_for_status()
        print(f"API Response: {response.json().get('message')}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error moving to position {position}: {e}")
        return False

def get_status():
    """Polls the actuator for its current status."""
    try:
        response = requests.get(f"{BASE_URL}/status")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error getting status: {e}")
        return None

def monitor_movement():
    """Polls the status endpoint every 0.5 seconds until movement stops."""
    while True:
        status = get_status()
        if status:
            current_pos = status.get('current_position', 'N/A')
            is_moving = status.get('is_moving', False)
            print(f"  [Polling] Current Position: {current_pos}, Is Moving: {is_moving}")
            if not is_moving:
                print(f"Movement finished. Final position: {current_pos}")
                break
        else:
            # Error getting status, stop monitoring
            break
        time.sleep(0.5)

def run_sequence():
    """Executes the full sequence of sash movements."""
    # 1. Go to Home position
    if move_to_position(1):
        monitor_movement()

    # Give it a moment before starting the sequence
    time.sleep(2)

    # 2. Cycle through all other positions
    for i in range(2, 6):
        if move_to_position(i):
            monitor_movement()
        # Pause before moving to the next position
        time.sleep(2)
    
    # 3. Return to home at the end
    if move_to_position(1):
        monitor_movement()

    print("\n✅ Sequence complete.")

if __name__ == "__main__":
    if not check_service_status():
        sys.exit(1)
        
    run_sequence() 
