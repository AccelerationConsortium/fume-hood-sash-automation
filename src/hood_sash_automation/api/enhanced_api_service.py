#!/usr/bin/env python3
"""
Enhanced Flask API Service for Fume Hood Sash Automation

This module provides an enhanced REST API with WebSocket support for real-time
monitoring and control of the fume hood sash actuator system.
"""

import signal
import yaml
import os
import json
import threading
import time
from datetime import datetime
from typing import Dict, Any, Optional

from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit, disconnect
from flask_cors import CORS

from ..actuator.controller import SashActuator
from ..actuator.buttons import PhysicalButtons
from ..sensor.sensor import SashSensor

def create_enhanced_app():
    """Create and configure an enhanced Flask application with WebSocket support."""
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'your-secret-key-here'
    
    # Enable CORS for all domains
    CORS(app, resources={r"/*": {"origins": "*"}})
    
    # Initialize SocketIO
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')
    
    def load_config():
        """Load configuration from YAML file."""
        config_path = os.path.join(os.getcwd(), 'users', 'config', 'actuator_config.yaml')
        if not os.path.exists(config_path):
            # Fallback for when running tests where CWD might be different
            config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'users', 'config', 'actuator_config.yaml'))
        
        with open(config_path, 'r') as f:
            actuator_config = yaml.safe_load(f)
        
        # Also load sensor config if available
        sensor_config_path = config_path.replace('actuator_config.yaml', 'sensor_config.yaml')
        sensor_config = {}
        if os.path.exists(sensor_config_path):
            with open(sensor_config_path, 'r') as f:
                sensor_config = yaml.safe_load(f)
        
        return actuator_config, sensor_config

    actuator_config, sensor_config = load_config()
    
    # Process actuator configuration
    actuator_hw_config = {
        'HALL_PINS': actuator_config['hall_pins'],
        'BOUNCE_MS': actuator_config['bounce_ms'],
        'RELAY_EXT': actuator_config['relay_ext_pin'],
        'RELAY_RET': actuator_config['relay_ret_pin'],
        'I2C_BUS': actuator_config['i2c_bus'],
        'INA_ADDR': actuator_config['ina_addr'],
        'R_SHUNT': actuator_config['r_shunt'],
        'I_MAX': actuator_config['i_max'],
        'CURRENT_THRESHOLD_UP': actuator_config['current_threshold_up'],
        'CURRENT_THRESHOLD_DOWN': actuator_config['current_threshold_down'],
        'MAX_MOVEMENT_TIME': actuator_config['max_movement_time'],
        'POSITION_TIMEOUT': actuator_config['position_timeout'],
        'POSITION_STATE_FILE': actuator_config['position_state_file'],
        'LOG_DIR': actuator_config['log_dir']
    }

    # Initialize hardware components
    actuator = SashActuator(actuator_hw_config)
    sensor = None
    
    # Initialize sensor if configuration is available
    if sensor_config:
        try:
            sensor = SashSensor(sensor_config)
        except Exception as e:
            print(f"Warning: Could not initialize sensor: {e}")
    
    # Attach to app instance
    app.actuator = actuator
    app.sensor = sensor
    app.socketio = socketio
    
    # Status broadcast thread
    status_thread = None
    status_thread_stop = threading.Event()
    
    def broadcast_status():
        """Broadcast status updates to connected clients."""
        while not status_thread_stop.is_set():
            try:
                status_data = get_comprehensive_status()
                socketio.emit('status_update', status_data, broadcast=True)
                time.sleep(1)  # Update every second
            except Exception as e:
                print(f"Error broadcasting status: {e}")
                time.sleep(5)  # Wait longer on error
    
    def get_comprehensive_status() -> Dict[str, Any]:
        """Get comprehensive system status."""
        try:
            actuator_status = app.actuator.get_status()
            
            # Get sensor status if available
            sensor_status = {}
            if app.sensor:
                try:
                    sensor_status = app.sensor.get_status()
                except Exception as e:
                    sensor_status = {"error": str(e)}
            
            # Combine status information
            status = {
                "timestamp": datetime.now().isoformat(),
                "actuator": actuator_status,
                "sensor": sensor_status,
                "system": {
                    "connected": True,
                    "uptime": time.time() - app.start_time if hasattr(app, 'start_time') else 0,
                    "version": "1.1.0"
                }
            }
            
            return status
            
        except Exception as e:
            return {
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "system": {
                    "connected": False,
                    "version": "1.1.0"
                }
            }
    
    # Store start time
    app.start_time = time.time()
    
    # REST API Routes
    
    @app.route('/api/v1/health', methods=['GET'])
    def health_check():
        """Health check endpoint."""
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "version": "1.1.0",
            "uptime": time.time() - app.start_time
        })
    
    @app.route('/api/v1/status', methods=['GET'])
    def get_status():
        """Get comprehensive system status."""
        return jsonify(get_comprehensive_status())
    
    @app.route('/api/v1/actuator/move', methods=['POST'])
    def move_actuator():
        """Move actuator to specified position."""
        data = request.get_json()
        if not data or 'position' not in data:
            return jsonify({"error": "Missing 'position' in request body"}), 400

        try:
            position = int(data['position'])
            if not 1 <= position <= 5:
                raise ValueError("Position out of range")
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid position. Must be an integer between 1 and 5."}), 400

        mode = data.get('mode', 'position')  # Default display mode
        
        if app.actuator.move_to_position_async(position, mode):
            # Broadcast immediate status update
            socketio.emit('movement_started', {
                "target_position": position,
                "mode": mode,
                "timestamp": datetime.now().isoformat()
            }, broadcast=True)
            
            return jsonify({
                "message": f"Moving to position {position}",
                "target_position": position,
                "mode": mode,
                "timestamp": datetime.now().isoformat()
            }), 202
        else:
            return jsonify({"message": "Actuator is already moving."}), 409

    @app.route('/api/v1/actuator/stop', methods=['POST'])
    def stop_actuator():
        """Stop actuator movement."""
        app.actuator.stop()
        
        # Broadcast stop event
        socketio.emit('movement_stopped', {
            "timestamp": datetime.now().isoformat()
        }, broadcast=True)
        
        return jsonify({
            "message": "Stop command issued.",
            "timestamp": datetime.now().isoformat()
        })

    @app.route('/api/v1/actuator/position', methods=['GET'])
    def get_actuator_position():
        """Get current actuator position."""
        position = app.actuator.get_current_position()
        return jsonify({
            "position": position,
            "timestamp": datetime.now().isoformat()
        })
    
    @app.route('/api/v1/actuator/home', methods=['POST'])
    def home_actuator():
        """Move actuator to home position (position 1)."""
        mode = request.get_json().get('mode', 'position') if request.get_json() else 'position'
        
        if app.actuator.move_to_position_async(1, mode):
            # Broadcast home event
            socketio.emit('movement_started', {
                "target_position": 1,
                "mode": mode,
                "type": "home",
                "timestamp": datetime.now().isoformat()
            }, broadcast=True)
            
            return jsonify({
                "message": "Moving to home position",
                "target_position": 1,
                "mode": mode,
                "timestamp": datetime.now().isoformat()
            }), 202
        else:
            return jsonify({"message": "Actuator is already moving."}), 409
    
    @app.route('/api/v1/actuator/config', methods=['GET'])
    def get_actuator_config():
        """Get actuator configuration."""
        return jsonify({
            "config": actuator_config,
            "timestamp": datetime.now().isoformat()
        })
    
    @app.route('/api/v1/sensor/status', methods=['GET'])
    def get_sensor_status():
        """Get sensor status."""
        if not app.sensor:
            return jsonify({"error": "Sensor not configured"}), 404
        
        try:
            status = app.sensor.get_status()
            return jsonify({
                "sensor": status,
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500
    
    @app.route('/api/v1/system/info', methods=['GET'])
    def get_system_info():
        """Get system information."""
        return jsonify({
            "system": {
                "name": "Fume Hood Sash Automation",
                "version": "1.1.0",
                "uptime": time.time() - app.start_time,
                "start_time": datetime.fromtimestamp(app.start_time).isoformat(),
                "current_time": datetime.now().isoformat(),
                "components": {
                    "actuator": True,
                    "sensor": app.sensor is not None,
                    "websocket": True
                }
            }
        })
    
    # Legacy endpoints for backward compatibility
    @app.route('/move', methods=['POST'])
    def legacy_move():
        """Legacy move endpoint for backward compatibility."""
        return move_actuator()
    
    @app.route('/stop', methods=['POST'])
    def legacy_stop():
        """Legacy stop endpoint for backward compatibility."""
        return stop_actuator()
    
    @app.route('/status', methods=['GET'])
    def legacy_status():
        """Legacy status endpoint for backward compatibility."""
        return get_status()
    
    @app.route('/position', methods=['GET'])
    def legacy_position():
        """Legacy position endpoint for backward compatibility."""
        return get_actuator_position()
    
    # WebSocket Events
    
    @socketio.on('connect')
    def handle_connect():
        """Handle WebSocket connection."""
        print(f"Client connected: {request.sid}")
        emit('connected', {
            "message": "Connected to Fume Hood Sash Automation",
            "timestamp": datetime.now().isoformat()
        })
        
        # Send initial status
        emit('status_update', get_comprehensive_status())
    
    @socketio.on('disconnect')
    def handle_disconnect():
        """Handle WebSocket disconnection."""
        print(f"Client disconnected: {request.sid}")
    
    @socketio.on('request_status')
    def handle_status_request():
        """Handle status request from client."""
        emit('status_update', get_comprehensive_status())
    
    @socketio.on('move_request')
    def handle_move_request(data):
        """Handle move request via WebSocket."""
        try:
            position = int(data.get('position', 1))
            mode = data.get('mode', 'position')
            
            if not 1 <= position <= 5:
                emit('error', {"message": "Invalid position. Must be between 1 and 5."})
                return
            
            if app.actuator.move_to_position_async(position, mode):
                emit('movement_started', {
                    "target_position": position,
                    "mode": mode,
                    "timestamp": datetime.now().isoformat()
                }, broadcast=True)
            else:
                emit('error', {"message": "Actuator is already moving."})
                
        except Exception as e:
            emit('error', {"message": str(e)})
    
    @socketio.on('stop_request')
    def handle_stop_request():
        """Handle stop request via WebSocket."""
        app.actuator.stop()
        emit('movement_stopped', {
            "timestamp": datetime.now().isoformat()
        }, broadcast=True)
    
    # Signal handlers for graceful shutdown
    def cleanup(signum, frame):
        """Cleanup function for graceful shutdown."""
        print("Caught signal, cleaning up...")
        
        # Stop status broadcast thread
        if status_thread and status_thread.is_alive():
            status_thread_stop.set()
            status_thread.join(timeout=5)
        
        # Cleanup hardware
        app.actuator.clean_exit()
        if app.sensor:
            app.sensor.cleanup()
        
        print("Cleanup complete")
        exit(0)

    signal.signal(signal.SIGINT, cleanup)
    signal.signal(signal.SIGTERM, cleanup)

    # Start physical button handler if not testing
    if os.environ.get("FLASK_ENV") != "testing":
        button_config = actuator_config.get('buttons', {})
        if button_config.get('up_pin') and button_config.get('down_pin'):
            button_handler = PhysicalButtons(
                app.actuator,
                up_pin=button_config['up_pin'],
                down_pin=button_config['down_pin'],
                stop_pin=button_config.get('stop_pin')
            )
            button_handler.start()
    
    # Start status broadcast thread
    status_thread = threading.Thread(target=broadcast_status, daemon=True)
    status_thread.start()
    
    return app, socketio

def main():
    """Main entry point for the enhanced API service."""
    app, socketio = create_enhanced_app()
    
    print("Starting Enhanced Fume Hood Sash Automation API...")
    print("REST API available at: http://0.0.0.0:5000")
    print("WebSocket available at: ws://0.0.0.0:5000")
    print("API Documentation:")
    print("  GET  /api/v1/health - Health check")
    print("  GET  /api/v1/status - Comprehensive status")
    print("  POST /api/v1/actuator/move - Move actuator")
    print("  POST /api/v1/actuator/stop - Stop actuator")
    print("  GET  /api/v1/actuator/position - Get position")
    print("  POST /api/v1/actuator/home - Move to home")
    print("  GET  /api/v1/system/info - System information")
    
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)

if __name__ == '__main__':
    main() 