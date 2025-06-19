#!/usr/bin/env python3
"""
Polls 5 Hall effect sensors every second using your HallArray class.
"""

import time
import signal
import sys
from hall import HallArray  # assumes hall.py is in the same directory

# Define the GPIO pins for your 5 Hall effect sensors
HALL_PINS = [5, 6, 13, 19, 26]  # BCM pin numbers
POLL_INTERVAL = 1  # seconds

# Create the HallArray instance
hall = HallArray(HALL_PINS)

def clean_exit(_sig=None, _frame=None):
    hall.close()
    sys.exit(0)

signal.signal(signal.SIGINT, clean_exit)
signal.signal(signal.SIGTERM, clean_exit)

print("Polling Hall sensor states every 1 second. Ctrl-C to exit.")

try:
    while True:
        states = hall.snapshot()
        output = "  ".join([f"H{i+1}:{'ON' if s == 0 else 'OFF'}" for i, s in enumerate(states)])
        print(output)
        time.sleep(POLL_INTERVAL)

except KeyboardInterrupt:
    clean_exit()
