# test_relay.py
#!/usr/bin/env python3
import time
import sys
import os

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.hood_sash_automation.actuator.relay import ActuatorRelay

# Change these if you wired to different pins
UP_PIN   = 17
DOWN_PIN = 27

relay = ActuatorRelay(up_pin=UP_PIN, down_pin=DOWN_PIN)

print("Testing relays. Ctrl‑C to stop.")
try:
    while True:
        print("→ UP on")
        relay.up_on()
        time.sleep(5)
        print("→ UP off")
        relay.up_off()
        time.sleep(0.5)

        print("→ DOWN on")
        relay.down_on()
        time.sleep(5)
        print("→ DOWN off")
        relay.down_off()
        time.sleep(0.5)

        print("→ BOTH off (brake)")
        relay.all_off()
        time.sleep(5)

except KeyboardInterrupt:
    pass

finally:
    relay.close()
    print("Cleaned up and exiting.")
