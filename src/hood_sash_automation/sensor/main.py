import RPi.GPIO as GPIO
import time
import logging
import os
import hashlib

# GPIO pin numbers (BCM numbering)
HALL_SENSOR_PIN = 17  # Input from hall effect sensor
LED_PIN = 27          # Output to LED

# Setup logging
LOG_FILE = "/var/log/sash_sensor_lite.log"
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logging.info("--- Sash Sensor Lite Startup ---")

# Log code version (SHA256 hash of this file)
def get_code_hash():
    try:
        with open(__file__, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()
    except Exception as e:
        return f"Error computing hash: {e}"

CODE_HASH = get_code_hash()
logging.info(f"Running sash_sensor_lite/main.py | SHA256: {CODE_HASH}")

def main():
    # Setup
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(HALL_SENSOR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Use pull-up resistor
    GPIO.setup(LED_PIN, GPIO.OUT)

    try:
        last_state = None
        while True:
            hall_state = GPIO.input(HALL_SENSOR_PIN)
            if hall_state == GPIO.LOW:
                # Magnet present (sash up) - turn LED on
                GPIO.output(LED_PIN, GPIO.HIGH)
            else:
                # Magnet not present (sash down) - turn LED off
                GPIO.output(LED_PIN, GPIO.LOW)
            if hall_state != last_state:
                if hall_state == GPIO.LOW:
                    print("State changed: Magnet present (sash up)")
                    logging.info("State changed: Magnet present (sash up)")
                else:
                    print("State changed: Magnet not present (sash down)")
                    logging.info("State changed: Magnet not present (sash down)")
                last_state = hall_state
            time.sleep(0.05)  # Polling delay
    except KeyboardInterrupt:
        logging.info("KeyboardInterrupt received. Exiting main loop.")
        pass
    finally:
        GPIO.cleanup()
        logging.info("GPIO cleanup complete. Program exiting.")
        logging.info("--- Sash Sensor Lite Session End ---")

if __name__ == "__main__":
    main()
