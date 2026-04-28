# API Guide

This folder contains the HTTP API used to control and monitor the fume hood sash
automation system.

## Active Services

### Actuator Service

The actuator service runs on port `5000` and is started with:

```bash
hood_sash_automation_actuator
```

The service is implemented in `api_service.py`. It controls the motorized sash,
reports position, and accepts movement commands.

### Sensor Service

The sensor service runs on port `5005` and is started with:

```bash
hood_sash_automation_sensor
```

The service is implemented in `../sensor/api_service.py`. It reports whether the
single-point hall sensor currently detects the sash magnet.

## Actuator API

Set the base URL for the actuator Pi:

```bash
PI=http://192.168.1.100:5000
# or with Tailscale:
PI=http://100.x.y.z:5000
```

Use the Pi Wi-Fi/LAN IP or Tailscale IP for your setup.

### Remote Computer Access

A laptop, dashboard computer, or another lab computer can interact with the
actuator API in a few ways.

#### Same Network or Tailscale

If the remote computer can reach the Raspberry Pi directly, call the API over
HTTP:

```bash
PI=http://192.168.1.100:5000
# or:
PI=http://100.x.y.z:5000

curl "$PI/status"
curl -X POST "$PI/move" \
  -H "Content-Type: application/json" \
  -d '{"position": 3}'
curl -X POST "$PI/stop"
```

This is the simplest option for a dashboard. The dashboard can use the same
URLs from browser or Python code.

#### Python Requests

Install `requests` on the remote computer:

```bash
pip install requests
```

Example:

```python
import requests
import time

BASE_URL = "http://100.x.y.z:5000"  # Pi Tailscale IP
# or:
# BASE_URL = "http://192.168.1.100:5000"  # Pi Wi-Fi/LAN IP

def get_status():
    return requests.get(f"{BASE_URL}/status", timeout=5).json()

def move_to(position):
    response = requests.post(
        f"{BASE_URL}/move",
        json={"position": position},
        timeout=5,
    )
    response.raise_for_status()
    return response.json()

def stop():
    return requests.post(f"{BASE_URL}/stop", timeout=5).json()

print(get_status())
print(move_to(3))

while get_status().get("is_moving"):
    print(get_status())
    time.sleep(0.5)
```

#### SSH Tunnel

If the Pi should not expose port `5000` directly on the network, create an SSH
tunnel from the remote computer:

```bash
ssh -L 5000:localhost:5000 pi@100.x.y.z
# or:
ssh -L 5000:localhost:5000 pi@192.168.1.100
```

Then, in another terminal on the remote computer:

```bash
PI=http://localhost:5000
curl "$PI/status"
curl -X POST "$PI/move" \
  -H "Content-Type: application/json" \
  -d '{"position": 3}'
```

The remote computer talks to `localhost:5000`, and SSH securely forwards that
traffic to the actuator service running on the Pi.

#### Existing Examples

The `examples/remote_control_example.py` script shows a direct HTTP client
that can run on a remote computer. The `examples/microservice_client.py`
script shows an SSH-based client that runs `curl` on the Pi through SSH.

### Health

```http
GET /health
```

Example:

```bash
curl "$PI/health"
```

Response:

```json
{
  "status": "healthy",
  "actuator": {
    "current_position": 3,
    "is_moving": false
  }
}
```

### Status

```http
GET /status
```

Example:

```bash
curl "$PI/status"
```

Response:

```json
{
  "current_position": 3,
  "is_moving": false
}
```

`current_position` is `null` when no position hall sensor is active.

### Position

```http
GET /position
```

Example:

```bash
curl "$PI/position"
```

Response:

```json
{
  "position": 3
}
```

### Move

```http
POST /move
Content-Type: application/json
```

Example:

```bash
curl -X POST "$PI/move" \
  -H "Content-Type: application/json" \
  -d '{"position": 3}'
```

Successful response:

```json
{
  "message": "Moving to position 3"
}
```

The service accepts positions `1` through `5`.

Invalid position response:

```json
{
  "error": "Invalid position. Must be an integer between 1 and 5."
}
```

Busy response:

```json
{
  "message": "Actuator is already moving."
}
```

### Stop

```http
POST /stop
```

Example:

```bash
curl -X POST "$PI/stop"
```

Response:

```json
{
  "message": "Stop command issued."
}
```

## Sensor API

Set the base URL for the sensor Pi:

```bash
SENSOR_PI=http://192.168.1.101:5005
# or with Tailscale:
SENSOR_PI=http://100.x.y.z:5005
```

### Sensor Status

```http
GET /status
```

Example:

```bash
curl "$SENSOR_PI/status"
```

Response:

```json
{
  "magnet_present": true
}
```

## Dashboard Notes

A future dashboard does not need a special API at first. It can use the actuator
API directly:

- Poll `GET /status` every `0.5` to `1` second.
- Show `current_position` and `is_moving`.
- Add buttons for positions `1` through `5` that call `POST /move`.
- Add an emergency stop button that calls `POST /stop`.

WebSockets can be added later if polling is not responsive enough.

## Safety Notes

- Keep `home_on_startup: false` while commissioning.
- Confirm the physical stop button or power cutoff is available before movement
  testing.
- Use `GET /status` before and after movement commands to confirm the sash state.
- Avoid sending repeated move commands while `is_moving` is `true`.
