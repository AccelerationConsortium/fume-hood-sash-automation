# main.py
#!/usr/bin/env python3
"""
main.py
• Monitors 5 Hall sensors + 2 limit switches (digital, active-LOW)
• Drives 2-channel relay board on CLI or named pipe command
• Typing 'position 1' or 'position 2' moves to limit switches 1 or 2
• Typing 'stop' interrupts movement
• Typing 'get' returns last reached position
• Logs sensor transitions and current draw
• Renders a PNG to the DFRobot LCD display when a position is reached
• Supports remote command input via /tmp/pipe
"""

import sys
import time
import signal
import select
import threading
import os

from switches import HallArray
from relay import ActuatorRelay
from current import CurrentSensor
from lcd_display_DFR0997 import DFRobotLCD

# -------- USER CONFIG --------
HALL_PINS  = [5, 6, 13, 19, 26]  # BCM pins for Hall sensors
LIMIT_PINS = [21, 20]            # BCM pins for Limit switches
ALL_PINS   = HALL_PINS + LIMIT_PINS

RELAY_EXT = 17                   # GPIO energises UP relay
RELAY_RET = 27                   # GPIO energises DOWN relay
BOUNCE_MS = 10                   # debounce in ms

I2C_BUS  = 1                     # Pi I2C bus
INA_ADDR = 0x45                  # INA219 address
R_SHUNT  = 0.1                   # Ω
I_MAX    = 3.0                   # A full-scale

DISPLAY_IMAGES = {
    1: "POS1.png",
    2: "POS2.png"
}

PIPE_PATH = "/tmp/pipe"
POSITION_STATE_FILE = "/tmp/position_state"
# -----------------------------

# initialize modules
relay   = ActuatorRelay(RELAY_EXT, RELAY_RET)
sensor  = CurrentSensor(address=INA_ADDR, busnum=I2C_BUS, r_shunt=R_SHUNT, i_max=I_MAX)
hall    = HallArray(ALL_PINS, bouncetime=BOUNCE_MS)
lcd     = DFRobotLCD()
lcd.begin()
lcd.clean_screen()

print(f"Calibration register: 0x{sensor.cal_value_read():04X}")

# sensor callback
def switch_callback(ch, state, idx):
    label = f"HALL {idx+1}" if idx < len(HALL_PINS) else f"LIMIT {idx+1 - len(HALL_PINS)}"
    print(f"{label} (GPIO{ch}) → {'ON' if state == 0 else 'OFF'}")

hall.set_callback(switch_callback)

# movement thread control
stop_flag = threading.Event()

# threaded actuator movement
def move_to_limit(index):
    stop_flag.clear()

    if index == 1:
        print("Moving UP to LIMIT 1...")
        relay.up_on()
        while hall.snapshot()[len(HALL_PINS)] != 0:
            if stop_flag.is_set():
                print("Stop requested. Aborting.")
                break
            time.sleep(0.01)

    elif index == 2:
        print("Moving DOWN to LIMIT 2...")
        relay.down_on()
        while hall.snapshot()[len(HALL_PINS)+1] != 0:
            if stop_flag.is_set():
                print("Stop requested. Aborting.")
                break
            time.sleep(0.01)
    else:
        print("Invalid position. Use 1 or 2.")

    relay.all_off()
    print("Movement complete.")

    # Show confirmation image if defined
    img = DISPLAY_IMAGES.get(index)
    if img:
        print(f"Displaying image: {img}")
        lcd.set_background_img(1, img)

    # Save last position
    try:
        with open(POSITION_STATE_FILE, "w") as f:
            f.write(str(index))
    except Exception as e:
        print(f"Failed to write position state: {e}")

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

signal.signal(signal.SIGINT,  clean_exit)
signal.signal(signal.SIGTERM, clean_exit)

# create named pipe if it doesn't exist
if not os.path.exists(PIPE_PATH):
    os.mkfifo(PIPE_PATH)

pipe_fd = os.open(PIPE_PATH, os.O_RDONLY | os.O_NONBLOCK)

print("System ready. Type 'position 1', 'position 2', 'stop', or 'get'. Ctrl-C to exit.")

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
            if cmd == "position 1":
                if move_thread and move_thread.is_alive():
                    print("Actuator already moving.")
                else:
                    move_thread = threading.Thread(target=move_to_limit, args=(1,))
                    move_thread.start()
            elif cmd == "position 2":
                if move_thread and move_thread.is_alive():
                    print("Actuator already moving.")
                else:
                    move_thread = threading.Thread(target=move_to_limit, args=(2,))
                    move_thread.start()
            elif cmd == "stop":
                stop_flag.set()
                print("Stop signal sent.")
            elif cmd == "get":
                try:
                    with open(POSITION_STATE_FILE, "r") as f:
                        state = f.read().strip()
                    print(f"Last reached position: {state}")
                except FileNotFoundError:
                    print("No position has been recorded yet.")
            else:
                print("Unknown command.")

        # print current every second
        amps = sensor.read_raw_shunt()
        print(f"Raw shunt: {amps}")
        time.sleep(.1)
    except KeyboardInterrupt:
        clean_exit()
