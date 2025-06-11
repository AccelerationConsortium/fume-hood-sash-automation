import logging
import os
from time import sleep

# Wait for filesystem to be fully ready
sleep(5)

LOG_FILE = "/var/log/sash_sensor_lite.log"
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logging.info("Pi booted - system startup")