#!/usr/bin/env python3
import signal
import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.hood_sash_automation.actuator.switches import HallArray  # your updated hall.py

# BCM pins for your 5 Hall sensors
HALL_PINS = [5, 6, 13, 19, 26]

# Create the HallArray (sets up GPIO interrupts)
hall = HallArray(HALL_PINS, bouncetime=10)

def hall_event(channel, state, idx):
    """
    Fires on every edge.  state==0 → magnet present (ON),
    state==1 → magnet absent (OFF).
    """
    if state == 0:
        print(f"🎯 Position {idx+1} reached (GPIO{channel})")
    else:
        print(f"⇦ Position {idx+1} left     (GPIO{channel})")

# Register the callback
hall.set_callback(hall_event)

def clean_exit(signum, frame):
    hall.close()
    sys.exit(0)

# Clean exit on Ctrl-C
signal.signal(signal.SIGINT, clean_exit)
signal.signal(signal.SIGTERM, clean_exit)

print("Watching Hall sensors—move a magnet near one to see a message. Ctrl-C to exit.")
signal.pause()  # wait here forever, callbacks do the work
