# src/hood_sash_automation/sensor/api_service.py
import signal
import logging
import yaml
import os
from flask import Flask, jsonify
from .sensor import SashSensor

def load_config():
    """Load configuration from YAML file."""
    config_path = os.path.join(os.getcwd(), 'users', 'config', 'sensor_config.yaml')
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)

# Load configuration
config = load_config()

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

app = Flask(__name__)
sensor = SashSensor(
    hall_pin=config['hall_sensor_pin'],
    led_pin=config['led_pin']
)

@app.route('/status', methods=['GET'])
def get_status():
    state = sensor.get_current_state()
    return jsonify({"magnet_present": state})

def cleanup(signum, frame):
    logging.info("Caught signal, cleaning up...")
    sensor.cleanup()
    exit(0)

def main():
    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    sensor.start()
    
    # Use a production-ready WSGI server like Gunicorn or uWSGI.
    app.run(host='0.0.0.0', port=5005, debug=False)

if __name__ == '__main__':
    main() 
