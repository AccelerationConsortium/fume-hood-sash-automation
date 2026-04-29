# src/hood_sash_automation/api/api_service.py
import signal
import yaml
import os
import socket
import fcntl
import struct
from pathlib import Path
from flask import Flask, request, jsonify
from ..actuator.controller import SashActuator
from ..actuator.buttons import PhysicalButtons

SIOCGIFADDR = 0x8915


def get_interface_ip(interface_name):
    """Return the IPv4 address for a network interface, or None if unavailable."""
    if not interface_name:
        return None

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        packed_name = struct.pack("256s", interface_name[:15].encode("utf-8"))
        return socket.inet_ntoa(fcntl.ioctl(sock.fileno(), SIOCGIFADDR, packed_name)[20:24])
    except OSError:
        return None
    finally:
        sock.close()


def create_app():
    """Create and configure an instance of the Flask application."""
    app = Flask(__name__)
    app.json.sort_keys = False

    def load_config():
        """Load configuration from YAML file."""
        config_path = Path(os.environ.get(
            "HOOD_SASH_ACTUATOR_CONFIG",
            Path(__file__).resolve().parents[1] / "config" / "actuator_config.yaml"
        ))
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)

    config = load_config()
    equipment_ip = config.get('equipment_ip') or get_interface_ip(
        config.get('equipment_ip_interface', 'wlan0')
    )
    equipment_tailscale = config.get('equipment_tailscale') or get_interface_ip(
        config.get('equipment_tailscale_interface', 'tailscale0')
    )
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
        'LOG_DIR': config['log_dir'],
        'HOME_ON_STARTUP': config.get('home_on_startup', False),
        'EQUIPMENT_NAME': config.get('equipment_name', 'fume_hood_sash_actuator'),
        'EQUIPMENT_IP': equipment_ip,
        'EQUIPMENT_TAILSCALE': equipment_tailscale,
    }

    actuator = SashActuator(actuator_config)
    app.actuator = actuator  # Attach actuator to the app instance

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

        if app.actuator.move_to_position_async(position):
            return jsonify(app.actuator.get_equipment_status(
                message=f"Moving sash to position {position}"
            )), 202
        else:
            return jsonify(app.actuator.get_equipment_status(
                message="Actuator is already moving."
            )), 409

    @app.route('/stop', methods=['POST'])
    def stop():
        app.actuator.stop()
        return jsonify(app.actuator.get_equipment_status(
            message="Stop command issued - System is STOPPED"
        ))

    @app.route('/status', methods=['GET'])
    def status():
        return jsonify(app.actuator.get_status())

    @app.route('/health', methods=['GET'])
    def health():
        return jsonify({
            "status": "healthy",
            "actuator": app.actuator.get_status()
        })

    @app.route('/equipment/status', methods=['GET'])
    def equipment_status():
        return jsonify(app.actuator.get_equipment_status())

    @app.route('/position', methods=['GET'])
    def get_position():
        position = app.actuator.get_current_position()
        return jsonify({"position": position})

    def cleanup(signum, frame):
        print("Caught signal, cleaning up...")
        app.actuator.clean_exit()
        exit(0)

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    # Start physical button handler in the app context if not testing
    if os.environ.get("FLASK_ENV") != "testing":
        button_config = config.get('buttons', {})
        if button_config.get('up_pin') and button_config.get('down_pin'):
            button_handler = PhysicalButtons(
                app.actuator,
                up_pin=button_config['up_pin'],
                down_pin=button_config['down_pin'],
                stop_pin=button_config.get('stop_pin')
            )
            button_handler.start()

    return app

def main():
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=False)

if __name__ == '__main__':
    main()
