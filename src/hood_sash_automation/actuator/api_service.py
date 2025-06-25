# src/hood_sash_automation/actuator/api_service.py
import signal
import yaml
import os
from flask import Flask, request, jsonify
from .controller import SashActuator
from .buttons import PhysicalButtons

def load_config():
    """Load configuration from YAML file."""
    # Assume the config file is in a 'config' directory at the project root.
    # The WorkingDirectory in the systemd service file should be the project root.
    config_path = os.path.join(os.getcwd(), 'config', 'actuator_config.yaml')
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

# Load configuration
config = load_config()

# Adapt the config dictionary for the classes
actuator_config = {
    'HALL_PINS': config['hall_pins'],
    'BOUNCE_MS': config['bounce_ms'],
    'RELAY_EXT': config['relay_ext_pin'],
    'RELAY_RET': config['relay_ret_pin'],
    'I2C_BUS': config['i2c_bus'],
    'INA_ADDR': config['ina_addr'],
    'R_SHUNT': config['r_shunt'],
    'I_MAX': config['i_max'],
    'CURRENT_THRESHOLD_UP': config['current_threshold_up'],
    'CURRENT_THRESHOLD_DOWN': config['current_threshold_down'],
    'MAX_MOVEMENT_TIME': config['max_movement_time'],
    'POSITION_TIMEOUT': config['position_timeout'],
    'POSITION_STATE_FILE': config['position_state_file'],
    'LOG_DIR': config['log_dir']
}

app = Flask(__name__)
actuator = SashActuator(actuator_config)

@app.route('/move', methods=['POST'])
def move():
    data = request.get_json()
    if not data or 'position' not in data:
        return jsonify({"error": "Missing 'position' in request body"}), 400
    
    try:
        position = int(data['position'])
        if not 1 <= position <= 5:
            raise ValueError("Position out of range")
    except (ValueError, TypeError):
        return jsonify({"error": "Invalid position. Must be an integer between 1 and 5."}), 400

    if actuator.move_to_position_async(position):
        return jsonify({"message": f"Moving to position {position}"}), 202
    else:
        return jsonify({"message": "Actuator is already moving."}), 409

@app.route('/stop', methods=['POST'])
def stop():
    actuator.stop()
    return jsonify({"message": "Stop command issued."})

@app.route('/status', methods=['GET'])
def status():
    return jsonify(actuator.get_status())

@app.route('/position', methods=['GET'])
def get_position():
    position = actuator.get_current_position()
    return jsonify({"position": position})


def cleanup(signum, frame):
    print("Caught signal, cleaning up...")
    actuator.clean_exit()
    exit(0)

def main():
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    # Start physical button handler
    button_config = config.get('buttons', {})
    if button_config.get('up_pin') and button_config.get('down_pin'):
        button_handler = PhysicalButtons(
            actuator,
            up_pin=button_config['up_pin'],
            down_pin=button_config['down_pin'],
            stop_pin=button_config.get('stop_pin') # stop_pin is optional
        )
        button_handler.start()
    
    app.run(host='0.0.0.0', port=5000, debug=False)

if __name__ == '__main__':
    main() 
    