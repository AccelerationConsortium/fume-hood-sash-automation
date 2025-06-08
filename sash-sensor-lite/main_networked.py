import RPi.GPIO as GPIO
import time
import threading
import socketserver
import logging
import os

# GPIO pin numbers (BCM numbering)
HALL_SENSOR_PIN = 17  # Input from hall effect sensor
LED_PIN = 27          # Output to LED

# Setup logging
LOG_FILE = os.path.join(os.path.dirname(__file__), "sash_sensor_lite.log")
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logging.info("--- Sash Sensor Lite Startup ---")

# Setup
GPIO.setmode(GPIO.BCM)
GPIO.setup(HALL_SENSOR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Use pull-up resistor
GPIO.setup(LED_PIN, GPIO.OUT)

# Functions to control/check hardware

def get_hall_state():
    """Returns True if magnet present (sash up), False if not (sash down)"""
    return GPIO.input(HALL_SENSOR_PIN) == GPIO.LOW

# List to keep track of connected clients
connected_clients = []

# TCP Server for remote commands and notifications
class CommandHandler(socketserver.BaseRequestHandler):
    def handle(self):
        # Add client to the list
        connected_clients.append(self.request)
        try:
            while True:
                data = self.request.recv(1024)
                if not data:
                    break  # Client disconnected
                cmd = data.strip().decode().lower()
                response = ""
                if cmd == "get":
                    response = f"magnet_present={get_hall_state()}"
                elif cmd == "status":
                    response = f"magnet_present={get_hall_state()}"
                elif cmd == "exit":
                    response = "shutting_down"
                    self.request.sendall(response.encode())
                    break
                else:
                    response = "unknown_command"
                self.request.sendall(response.encode())
        finally:
            # Remove client from the list on disconnect
            if self.request in connected_clients:
                connected_clients.remove(self.request)

class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True

# Main sensor/LED loop

def sensor_loop():
    last_state = None
    try:
        while True:
            state = get_hall_state()
            GPIO.output(LED_PIN, GPIO.HIGH if state else GPIO.LOW)
            if state != last_state:
                msg = f"sensor_changed: magnet_present={state}\n"
                # Log the state change
                if state:
                    logging.info("State changed: Magnet present (sash up)")
                else:
                    logging.info("State changed: Magnet not present (sash down)")
                # Notify all clients
                for client in connected_clients[:]:
                    try:
                        client.sendall(msg.encode())
                    except Exception:
                        connected_clients.remove(client)
                last_state = state
            time.sleep(0.05)
    except KeyboardInterrupt:
        logging.info("KeyboardInterrupt received. Exiting sensor loop.")
        pass
    finally:
        GPIO.cleanup()
        logging.info("GPIO cleanup complete. Program exiting.")

if __name__ == "__main__":
    # Start sensor loop in background
    t = threading.Thread(target=sensor_loop, daemon=True)
    t.start()

    # Start TCP server
    HOST, PORT = "", 5005  # Listen on all interfaces, port 5005
    with ThreadedTCPServer((HOST, PORT), CommandHandler) as server:
        print(f"sash-sensor-lite server running on port {PORT}")
        try:
            server.serve_forever()
        except (KeyboardInterrupt, SystemExit):
            print("Shutting down server...")
            GPIO.cleanup()
            logging.info("Server shutdown complete.")
