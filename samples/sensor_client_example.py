import socket

def send_command(host, port, command):
    """Send a command to the sash-sensor-lite server and return the response."""
    with socket.create_connection((host, port), timeout=2) as sock:
        sock.sendall(command.encode())
        response = sock.recv(1024).decode()
        return response

if __name__ == "__main__":
    PI_IP = "192.168.1.100"  # Replace with your Pi's static IP
    PORT = 5005

    # Query sensor state
    print("Sensor state:", send_command(PI_IP, PORT, "get"))

    # Get full status
    print("Status:", send_command(PI_IP, PORT, "status"))
