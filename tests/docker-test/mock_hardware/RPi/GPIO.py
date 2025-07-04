"""
A mock RPi.GPIO library to simulate GPIO operations for testing on non-Pi hardware.
This allows the application code to run unmodified inside a Docker container.
"""

import logging

# --- Mock State ---
# This dictionary will store the state of all GPIO pins.
# Example: _pins = {17: {'mode': OUT, 'value': LOW, 'pud': None}, 27: {...}}
_pins = {}
_pin_mode = None

# --- Constants ---
# These constants mimic the real RPi.GPIO constants.
BCM = 11
BOARD = 10
OUT = 0
IN = 1
HIGH = 1
LOW = 0
PUD_UP = 22
PUD_DOWN = 21
PUD_OFF = 20
BOTH = 33
FALLING = 32
RISING = 31

# --- Logging ---
logging.basicConfig(level=logging.INFO, format='[MockGPIO] %(message)s')

# --- Mock Functions ---
def setmode(mode):
    """Sets the pin numbering mode (BCM or BOARD)."""
    global _pin_mode
    if mode not in [BCM, BOARD]:
        raise ValueError("Invalid mode specified. Must be BCM or BOARD.")
    _pin_mode = mode
    logging.info(f"GPIO mode set to {'BCM' if mode == BCM else 'BOARD'}")

def setup(channel, mode, pull_up_down=PUD_OFF, initial=LOW):
    """Sets up a GPIO channel or list of channels."""
    pins_to_setup = channel if isinstance(channel, list) else [channel]
    for pin in pins_to_setup:
        if pin in _pins:
            logging.warning(f"Pin {pin} is already configured. Re-configuring.")
        _pins[pin] = {'mode': mode, 'value': initial, 'pud': pull_up_down, 'event': None}
        logging.info(f"Pin {pin} setup as {'OUT' if mode == OUT else 'IN'} with pull_up_down={pull_up_down}")
        if mode == OUT:
            _pins[pin]['value'] = initial

def output(channel, value):
    """Sets the output value of a GPIO pin."""
    pins_to_set = channel if isinstance(channel, list) else [channel]
    for pin in pins_to_set:
        if pin not in _pins or _pins[pin]['mode'] != OUT:
            raise RuntimeError(f"Pin {pin} has not been set up as an output.")
        _pins[pin]['value'] = value
        # In a real mock, you could trigger events here.

def input(channel):
    """Reads the value of a GPIO pin."""
    if channel not in _pins or _pins[channel]['mode'] != IN:
        raise RuntimeError(f"Pin {channel} has not been set up as an input.")
    # Return the current value, or default to HIGH if it's a pull-up.
    if _pins[channel]['pud'] == PUD_UP:
        return _pins[channel].get('value', HIGH)
    return _pins[channel].get('value', LOW)

def add_event_detect(channel, edge, callback=None, bouncetime=None):
    """Adds event detection for a GPIO pin (mocked)."""
    if channel not in _pins:
        raise RuntimeError(f"Pin {channel} has not been set up yet.")
    _pins[channel]['event'] = {'edge': edge, 'callback': callback, 'bouncetime': bouncetime}
    logging.info(f"Event detection added for pin {channel} on edge {'BOTH' if edge == BOTH else 'N/A'}")

def cleanup(channel=None):
    """Resets GPIO pin configurations."""
    global _pins, _pin_mode
    if channel:
        pins_to_clean = channel if isinstance(channel, list) else [channel]
        for pin in pins_to_clean:
            if pin in _pins:
                del _pins[pin]
        logging.info(f"Cleaned up specified GPIO channels: {pins_to_clean}")
    else:
        _pins.clear()
        _pin_mode = None
        logging.info("Cleaned up all GPIO channels.")

# --- Helper for testing ---
def set_pin_value(channel, value):
    """A helper function for tests to manually set a pin's input value."""
    if channel in _pins and _pins[channel]['mode'] == IN:
        _pins[channel]['value'] = value
        # If there's a callback registered, simulate the event
        event = _pins[channel].get('event')
        if event and event['callback']:
            event['callback'](channel)
    else:
        raise RuntimeError(f"Cannot set value for unconfigured or output pin {channel}.")

def get_pin_state(channel):
    """A helper to inspect a pin's state during tests."""
    return _pins.get(channel)