import requests


if __name__ == "__main__":
    SENSOR_HOST = "100.x.y.z"  # Replace with your sensor Pi Tailscale or Wi-Fi IP.
    SENSOR_PORT = 5005
    base_url = f"http://{SENSOR_HOST}:{SENSOR_PORT}"

    response = requests.get(f"{base_url}/status", timeout=5)
    response.raise_for_status()
    print("Sensor status:", response.json())
