# src/hood_sash_automation/actuator/controller.py
import time
import threading
import logging
import os
import datetime

from .switches import HallArray
from .relay import ActuatorRelay
from .current import CurrentSensor
from .lcd_display_DFR0997 import DFRobotLCD

class SashActuator:
    def __init__(self, config):
        self.config = config
        
        # Setup logging
        self._setup_logging()

        # Initialize hardware components
        self.relay = ActuatorRelay(config['RELAY_EXT'], config['RELAY_RET'])
        self.sensor = CurrentSensor(address=config['INA_ADDR'], busnum=config['I2C_BUS'], 
                                    r_shunt=config['R_SHUNT'], i_max=config['I_MAX'])
        self.hall = HallArray(config['HALL_PINS'], bouncetime=config['BOUNCE_MS'])
        self.lcd = DFRobotLCD()
        self.lcd.begin()
        self.lcd.clean_screen()

        logging.info(f"Calibration register: 0x{self.sensor.cal_value_read():04X}")

        self.current_position = None
        self.hall.set_callback(self.hall_callback)
        self.stop_flag = threading.Event()
        self.movement_thread = None

        self.display_mode = 'position' # Default display mode

        self.home_on_startup()


    def _setup_logging(self):
        LOG_DIR = self.config.get("LOG_DIR", "/var/log/sash_actuator")
        os.makedirs(LOG_DIR, exist_ok=True)
        SESSION_TIMESTAMP = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        LOG_FILE = os.path.join(LOG_DIR, f"session_{SESSION_TIMESTAMP}.log")
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            handlers=[
                logging.FileHandler(LOG_FILE),
                logging.StreamHandler()
            ]
        )

    def hall_callback(self, ch, state, idx):
        if state == 0:  # Magnet detected
            self.current_position = idx + 1
            logging.info(f"Position {self.current_position} reached (Hall sensor {idx})")
            if self.display_mode is not None:
                self.display_image(self.current_position, self.display_mode)
        else:
            logging.info(f"Left position {idx + 1} (Hall sensor {idx})")

    def get_current_position(self):
        states = self.hall.snapshot()
        for idx, state in enumerate(states):
            if state == 0:
                return idx + 1
        return None

    def move_to_position_async(self, target_pos, mode=None):
        if self.movement_thread and self.movement_thread.is_alive():
            logging.warning("Movement already in progress.")
            return False

        if mode is None:
            mode = self.display_mode

        self.movement_thread = threading.Thread(target=self.move_to_position, args=(target_pos, mode))
        self.movement_thread.start()
        return True

    def move_to_position(self, target_pos, mode):
        logging.info(f"Attempting to move actuator to position {target_pos} in mode {mode}")
        if not 1 <= target_pos <= 5:
            logging.error(f"Invalid position {target_pos}. Use positions 1-5.")
            return

        self.stop_flag.clear()
        current_pos = self.get_current_position()

        if current_pos == target_pos:
            logging.info(f"Already at position {target_pos}")
            return

        if current_pos is None:
            logging.info("Position unknown - searching with downward pulses...")
            for pulse in range(5):
                if self.stop_flag.is_set():
                    logging.info("Stop requested during position search.")
                    self.relay.all_off()
                    return
                logging.info(f"Pulse {pulse + 1}/5...")
                self._pulse_down()
                current_pos = self.current_position
                if current_pos is not None:
                    logging.info(f"Found position {current_pos}")
                    time.sleep(0.1)
                    break
            else:
                logging.error("Could not determine position after 5 pulses")
                return

        if current_pos < target_pos:
            logging.info(f"Moving UP from position {current_pos} to position {target_pos}")
            direction = "up"
            self.relay.up_on()
        else:
            logging.info(f"Moving DOWN from position {current_pos} to position {target_pos}")
            direction = "down"
            self.relay.down_on()
        
        time.sleep(0.5) # delay to skip initial current spike

        start_time = time.time()
        last_valid_time = start_time
        last_valid_pos = current_pos

        while self.current_position != target_pos:
            if self.stop_flag.is_set():
                logging.info("Stop requested during movement.")
                break

            if time.time() - start_time > self.config['MAX_MOVEMENT_TIME']:
                logging.error("Movement timed out.")
                break
            
            if not self._check_movement_current(direction):
                logging.warning("Collision detected based on current.")
                break

            last_valid_time, last_valid_pos = self._validate_movement_sequence(
                current_pos, target_pos, direction, last_valid_time, last_valid_pos
            )

            time.sleep(0.01)

        self.relay.all_off()
        logging.info(f"Movement finished. Final position: {self.current_position}")
        self._write_position_state()


    def stop(self):
        self.stop_flag.set()
        if self.movement_thread and self.movement_thread.is_alive():
            self.movement_thread.join()
        self.relay.all_off()
        logging.info("Movement stopped by user.")

    def home_on_startup(self, mode=None):
        if mode is None:
            mode = self.display_mode
            
        logging.info("Homing actuator on startup...")
        self.move_to_position_async(1, mode) # Move to position 1 (home)

    def clean_exit(self):
        logging.info("Cleaning up resources.")
        self.stop()
        self.hall.close()
        self.lcd.clean_screen()

    def _pulse_down(self):
        self.relay.down_on()
        time.sleep(1)
        start_time = time.time()
        initial_position = self.current_position
        while time.time() - start_time < 1.0:
            if not self._check_movement_current("down"):
                self.relay.all_off()
                return False
            if self.current_position is not None and self.current_position != initial_position:
                self.relay.all_off()
                return True
            time.sleep(0.01)
        self.relay.all_off()
        time.sleep(0.2)
        return True

    def _check_movement_current(self, direction):
        amps = self.sensor.read_raw_shunt()
        if direction == "up" and amps > self.config['CURRENT_THRESHOLD_UP']:
            logging.warning(f"Collision current detected during upward movement: {amps}")
            return False
        elif direction == "down" and amps < self.config['CURRENT_THRESHOLD_DOWN']:
            logging.warning(f"Collision current detected during downward movement: {amps}")
            return False
        return True

    def _validate_movement_sequence(self, start_pos, target_pos, direction, last_valid_time, last_valid_pos):
        current_time = time.time()
        current_pos = self.get_current_position()

        if current_time - last_valid_time > self.config['POSITION_TIMEOUT']:
            logging.warning(f"No position detected for {self.config['POSITION_TIMEOUT']} seconds.")
            return current_time, last_valid_pos

        if current_pos is not None:
            if direction == "up":
                expected_positions = range(start_pos + 1, target_pos + 1)
                if current_pos in expected_positions and current_pos > last_valid_pos:
                     if current_pos != start_pos + 1 and current_pos != last_valid_pos + 1:
                        logging.warning(f"Missed position(s) between {last_valid_pos} and {current_pos}")
                     return current_time, current_pos
            else: # down
                expected_positions = range(start_pos - 1, target_pos - 1, -1)
                if current_pos in expected_positions and current_pos < last_valid_pos:
                    if current_pos != start_pos - 1 and current_pos != last_valid_pos - 1:
                        logging.warning(f"Missed position(s) between {last_valid_pos} and {current_pos}")
                    return current_time, current_pos
        return last_valid_time, last_valid_pos

    def display_image(self, position, mode):
        # This is a placeholder for the actual image display logic from main.py
        # You would need to adapt the image loading and displaying code here.
        logging.info(f"Displaying image for position {position} in mode {mode}")
        image_path = f"/home/pi/sash/images/{mode}{position}.png"
        if os.path.exists(image_path):
            self.lcd.display_image(image_path)
        else:
            logging.warning(f"Image not found: {image_path}")

    def get_status(self):
        return {
            "current_position": self.current_position,
            "is_moving": self.movement_thread.is_alive() if self.movement_thread else False,
        }
    
    def _write_position_state(self):
        POSITION_STATE_FILE = self.config.get("POSITION_STATE_FILE", "/tmp/position_state")
        try:
            with open(POSITION_STATE_FILE, "w") as f:
                f.write(str(self.current_position))
        except IOError as e:
            logging.error(f"Failed to write position state to {POSITION_STATE_FILE}: {e}") 