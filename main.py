# main.py
#!/usr/bin/env python3
"""
main.py
• Monitors 5 Hall sensors for position feedback
• Drives 2-channel relay board for up/down movement
• Commands:
  - 'position N' (N=1-5): moves to specified hall sensor position
  - 'stop': interrupts movement
  - 'get': returns current position
• Logs sensor transitions and current draw
• Renders display based on mode:
  - position: Shows position numbers (POS1.png, POS2.png, etc.)
  - thumb: Shows thumbnails (thumb1.png, thumb2.png, etc.)
  - kirby: Shows animated GIFs (kirby_1_speed.gif, etc.)
• Supports remote command input via /tmp/pipe
"""

import sys
import time
import signal
import select
import threading
import os
import argparse

from switches import HallArray
from relay import ActuatorRelay
from current import CurrentSensor
from lcd_display_DFR0997 import DFRobotLCD

# -------- USER CONFIG --------
HALL_PINS = [5, 6, 13, 19, 26]  # BCM pins for Hall sensors
BOUNCE_MS = 10                   # debounce in ms

RELAY_EXT = 27                   # GPIO energises UP relay
RELAY_RET = 17                   # GPIO energises DOWN relay

I2C_BUS  = 1                     # Pi I2C bus
INA_ADDR = 0x45                  # INA219 address
R_SHUNT  = 0.1                   # Ω
I_MAX    = 3.0                   # A full-scale

# Current thresholds for collision detection
CURRENT_THRESHOLD_UP = 2000    # Raw shunt value threshold when moving up
CURRENT_THRESHOLD_DOWN = 2000   # Raw shunt value threshold when moving down
CURRENT_SAMPLES = 2           # Number of consecutive samples needed to trigger

# Current monitoring thresholds
MIN_EXPECTED_CURRENT_UP = -5   # Minimum expected current when moving up
MAX_EXPECTED_CURRENT_UP = 1500   # Maximum normal current when moving up (below collision threshold)
MIN_EXPECTED_CURRENT_DOWN = -5  # Minimum expected current when moving down

# Position sequence validation
SEQUENCE_CHECK_INTERVAL = 0.1  # How often to check for missed positions (seconds)

# Movement timeouts
MAX_MOVEMENT_TIME = 10.0     # Maximum time for movement between positions (seconds)
POSITION_TIMEOUT = 2.0       # Maximum time between expected positions (seconds)

PIPE_PATH = "/tmp/pipe"
POSITION_STATE_FILE = "/tmp/position_state"
# -----------------------------

# initialize modules
relay = ActuatorRelay(RELAY_EXT, RELAY_RET)
sensor = CurrentSensor(address=INA_ADDR, busnum=I2C_BUS, r_shunt=R_SHUNT, i_max=I_MAX)
hall = HallArray(HALL_PINS, bouncetime=BOUNCE_MS)
lcd = DFRobotLCD()
lcd.begin()
lcd.clean_screen()

print(f"Calibration register: 0x{sensor.cal_value_read():04X}")

# Current position tracking
current_position = None
def hall_callback(ch, state, idx):
    global current_position
    if state == 0:  # Magnet detected
        current_position = idx + 1
        print(f"Position {current_position} reached (GPIO{ch})")
    else:
        print(f"Left position {idx + 1} (GPIO{ch})")

hall.set_callback(hall_callback)

# movement thread control
stop_flag = threading.Event()

def get_current_position():
    """Returns the current position based on hall sensor states"""
    states = hall.snapshot()
    for idx, state in enumerate(states):
        if state == 0:  # Active LOW - magnet present
            return idx + 1
    return None

def check_current_threshold(threshold):
    """Check if current exceeds threshold for multiple samples"""
    high_current_count = 0
    for _ in range(CURRENT_SAMPLES):
        amps = sensor.read_raw_shunt()
        if amps > threshold:
            high_current_count += 1
        else:
            high_current_count = 0  # Reset on any low reading
        time.sleep(0.01)  # Small delay between readings
    return high_current_count == CURRENT_SAMPLES

def pulse_down():
    """Pulse the down relay for 1 second"""
    relay.down_on()
    start_time = time.time()
    while time.time() - start_time < 1.0:
        if check_current_threshold(CURRENT_THRESHOLD_DOWN):
            print("WARNING: High current detected during pulse - possible collision!")
            relay.all_off()
            return False
        time.sleep(0.01)
    relay.all_off()
    time.sleep(0.2)  # Small pause between pulses
    return True

def validate_movement_sequence(start_pos, target_pos, direction, last_valid_time, last_valid_pos):
    """Check if we're hitting expected positions in sequence"""
    current_time = time.time()
    current_pos = get_current_position()
    
    # If we haven't seen a position for too long
    if current_time - last_valid_time > POSITION_TIMEOUT:
        print(f"WARNING: No position detected for {POSITION_TIMEOUT} seconds - check hall sensors")
        return current_time, last_valid_pos  # Reset timer to avoid repeated warnings
        
    # If we have a position reading
    if current_pos is not None:
        # Moving up should trigger positions in ascending order
        if direction == "up":
            expected_positions = range(start_pos + 1, target_pos + 1)
            if current_pos in expected_positions:
                if current_pos != start_pos + 1 and current_pos != last_valid_pos + 1:
                    print(f"WARNING: Missed position(s) between {last_valid_pos} and {current_pos}")
                return current_time, current_pos
        # Moving down should trigger positions in descending order
        else:  # direction == "down"
            expected_positions = range(start_pos - 1, target_pos - 1, -1)
            if current_pos in expected_positions:
                if current_pos != start_pos - 1 and current_pos != last_valid_pos - 1:
                    print(f"WARNING: Missed position(s) between {last_valid_pos} and {current_pos}")
                return current_time, current_pos
                
    return last_valid_time, last_valid_pos

def check_movement_current(direction):
    """Verify current readings are in expected range for movement direction"""
    amps = sensor.read_raw_shunt()
    
    if direction == "up":
        if amps < MIN_EXPECTED_CURRENT_UP:
            print(f"WARNING: Current too low for upward movement ({amps}) - check if actuator is engaged")
            return False
        elif MIN_EXPECTED_CURRENT_UP <= amps <= MAX_EXPECTED_CURRENT_UP:
            return True
        elif amps > CURRENT_THRESHOLD_UP:
            return False  # Will be handled by collision detection
    else:  # direction == "down"
        if amps < MIN_EXPECTED_CURRENT_DOWN:
            print(f"WARNING: Current too low for downward movement ({amps}) - check if actuator is engaged")
            return False
        elif amps > CURRENT_THRESHOLD_DOWN:
            return False  # Will be handled by collision detection
    return True

def move_to_position(target_pos, mode):
    """Move to specified position (1-5)"""
    if not 1 <= target_pos <= 5:
        print("Invalid position. Use positions 1-5.")
        return

    stop_flag.clear()
    current_pos = get_current_position()
    
    if current_pos == target_pos:
        print(f"Already at position {target_pos}")
        return

    # For unknown position, search with downward pulses
    if current_pos is None:
        print("Position unknown - searching with downward pulses...")
        
        # Try up to 5 pulses to find position
        for pulse in range(5):
            if stop_flag.is_set():
                print("Stop requested. Aborting.")
                relay.all_off()
                return
                
            print(f"Pulse {pulse + 1}/5...")
            if not pulse_down():  # Stop if collision detected
                print("Search aborted due to possible collision.")
                return
            
            pos = get_current_position()
            if pos is not None:
                print(f"Found position {pos}")
                current_pos = pos
                time.sleep(0.1)  # Short pause before continuing
                break
        else:
            print("ERROR: Could not determine position after 5 pulses.")
            print("Please manually move the actuator to a known position (aligned with a hall sensor).")
            return
    
    # Now we know our position, move to target
    if current_pos < target_pos:
        print(f"Moving UP from position {current_pos} to position {target_pos}...")
        direction = "up"
        relay.up_on()
        current_threshold = CURRENT_THRESHOLD_UP
    else:
        print(f"Moving DOWN from position {current_pos} to position {target_pos}...")
        direction = "down"
        relay.down_on()
        current_threshold = CURRENT_THRESHOLD_DOWN

    # Wait for target position or stop signal
    movement_start_time = time.time()
    last_valid_time = movement_start_time
    last_valid_pos = current_pos
    next_sequence_check = movement_start_time
    reached_positions = {current_pos}  # Track positions we've seen
    
    while time.time() - movement_start_time < MAX_MOVEMENT_TIME:
        if stop_flag.is_set():
            print("Stop requested. Aborting.")
            break
            
        current_time = time.time()
        
        # Check movement sequence periodically
        if current_time >= next_sequence_check:
            last_valid_time, last_valid_pos = validate_movement_sequence(
                current_pos, target_pos, direction, last_valid_time, last_valid_pos)
            next_sequence_check = current_time + SEQUENCE_CHECK_INTERVAL
            
        # Monitor current for movement issues
        if not check_movement_current(direction):
            if check_current_threshold(current_threshold):
                print("WARNING: High current detected - possible collision! Stopping movement.")
                break
        
        pos = get_current_position()
        if pos is not None:
            reached_positions.add(pos)
        if pos == target_pos:
            print(f"Target position {target_pos} reached!")
            break
        elif pos is None:
            print("Warning: Lost position tracking during movement")
            
        time.sleep(0.01)
    else:
        print("Movement timed out. Please check for mechanical issues.")

    relay.all_off()
    print("Movement complete.")

    # Verify final position and expected sequence
    final_pos = get_current_position()
    if final_pos == target_pos:
        if direction == "up" and not all(i in reached_positions for i in range(current_pos + 1, target_pos)):
            print("WARNING: Some positions were missed during upward movement - hall sensors may need adjustment")
        elif direction == "down" and not all(i in reached_positions for i in range(target_pos + 1, current_pos)):
            print("WARNING: Some positions were missed during downward movement - hall sensors may need adjustment")
            
        # Show appropriate display for the mode
        display_image(target_pos, mode)

        # Save last position
        try:
            with open(POSITION_STATE_FILE, "w") as f:
                f.write(str(target_pos))
        except Exception as e:
            print(f"Failed to write position state: {e}")

def is_fumehood_ready():
    """Check if the sash is in position 5 (fully open)"""
    return get_current_position() == 5

def display_image(position, mode):
    """Display the appropriate image/animation based on mode and position"""
    if position not in [1, 2, 3, 4, 5, "homing"]:
        return
        
    image = DISPLAY_CONFIGS[mode][position]
    
    if mode == "kirby" and position != "homing":
        print(f"Displaying GIF: {image}")
        lcd.draw_gif_external(0, 0, image, zoom=255)
    else:
        print(f"Displaying image: {image}")
        lcd.set_background_img(1, image)

def home_on_startup(mode):
    """Initialize system and move to home position (position 1)"""
    print("System starting up - preparing to home...")
    display_image("homing", mode)
    print("Waiting 10 seconds before homing sequence...")
    time.sleep(10)
    
    print("Starting homing sequence...")
    move_to_position(1, mode)
    
    if get_current_position() == 1:
        print("Homing complete - system ready")
        return True
    else:
        print("WARNING: Homing failed - manual intervention may be required")
        return False

# clean exit handler
def clean_exit(_sig=None,_frame=None):
    stop_flag.set()
    hall.close()
    relay.close()
    sensor.close()
    lcd.clean_screen()
    try:
        os.unlink(PIPE_PATH)
    except FileNotFoundError:
        pass
    sys.exit(0)

signal.signal(signal.SIGINT, clean_exit)
signal.signal(signal.SIGTERM, clean_exit)

# Display configurations for different modes
DISPLAY_CONFIGS = {
    "position": {
        "homing": "homing.png",
        1: "POS1.png",
        2: "POS2.png",
        3: "POS3.png",
        4: "POS4.png",
        5: "POS5.png"
    },
    "thumb": {
        "homing": "homing.png",
        1: "thumb1.png",
        2: "thumb2.png",
        3: "thumb3.png",
        4: "thumb4.png",
        5: "thumb5.png"
    },
    "kirby": {
        "homing": "homing.png",
        1: "kirby_1_speed.gif",
        2: "kirby_2_speed.gif",
        3: "kirby_3_speed.gif",
        4: "kirby_4_speed.gif",
        5: "kirby_5_speed.gif"
    }
}

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Fume hood sash control with different display modes')
    parser.add_argument('mode', choices=['position', 'thumb', 'kirby'],
                      help='Display mode: position (position numbers), thumb (thumbs), or kirby (gifs)')
    args = parser.parse_args()

    global DISPLAY_IMAGES
    DISPLAY_IMAGES = DISPLAY_CONFIGS[args.mode]

    # Initialize system
    print(f"Starting in {args.mode} mode")
    print(f"Calibration register: 0x{sensor.cal_value_read():04X}")

    # Perform homing sequence
    home_on_startup(args.mode)

    # create named pipe if it doesn't exist
    if not os.path.exists(PIPE_PATH):
        os.mkfifo(PIPE_PATH)

    pipe_fd = os.open(PIPE_PATH, os.O_RDONLY | os.O_NONBLOCK)

    print("System ready. Commands: 'position N' (N=1-5), 'stop', 'get', or 'check_ready'. Ctrl-C to exit.")

    move_thread = None

    def read_command():
        if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
            return input().strip().lower()
        try:
            data = os.read(pipe_fd, 1024).decode().strip()
            return data if data else None
        except BlockingIOError:
            return None

    while True:
        try:
            cmd = read_command()
            if cmd:
                if cmd.startswith("position "):
                    try:
                        pos = int(cmd.split()[1])
                        if 1 <= pos <= 5:
                            if move_thread and move_thread.is_alive():
                                print("Actuator already moving.")
                            else:
                                move_thread = threading.Thread(target=move_to_position, args=(pos, args.mode))
                                move_thread.start()
                        else:
                            print("Invalid position. Use positions 1-5.")
                    except (IndexError, ValueError):
                        print("Invalid command format. Use 'position N' where N is 1-5.")
                elif cmd == "stop":
                    stop_flag.set()
                    print("Stop signal sent.")
                elif cmd == "get":
                    pos = get_current_position()
                    if pos is not None:
                        print(f"Current position: {pos}")
                    else:
                        print("Position unknown (no hall sensor active)")
                elif cmd == "check_ready":
                    if is_fumehood_ready():
                        print("Fumehood is ready - sash fully open")
                    else:
                        print("Fumehood not ready - sash not fully open")
                else:
                    print("Unknown command.")

            time.sleep(.1)
        except KeyboardInterrupt:
            clean_exit()

if __name__ == "__main__":
    main()
