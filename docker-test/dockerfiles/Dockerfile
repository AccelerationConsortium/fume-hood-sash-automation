# Dockerfile for fume-hood-sash-automation

# --- Stage 1: Builder ---
# This stage installs all dependencies, including test and mock libraries,
# and builds the package.
# Using official Raspberry Pi OS Docker image with Python 3.11 and Debian 12 (bookworm)
FROM dtcooper/raspberrypi-os:python3.11-bookworm AS builder

WORKDIR /app

# Install system dependencies that might be needed by Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Note: RPi.GPIO and related libraries are already available in the 
# official Raspberry Pi OS Docker image, no need for fake-rpigpio

# Copy project files
COPY pyproject.toml README.md ./
COPY src ./src

# Install the project with all its dependencies.
# The mock libraries we installed above will satisfy the hardware requirements.
RUN pip install .[actuator,sensor]


# --- Stage 2: Final ---
# This stage creates the final, lean image. It copies the installed
# application from the builder stage, but not the build tools or extra libraries.
# Using official Raspberry Pi OS Docker image with Python 3.11 and Debian 12 (bookworm)
FROM dtcooper/raspberrypi-os:python3.11-bookworm

WORKDIR /app

# Create a non-root user to run the application for better security
RUN useradd --create-home appuser
USER appuser

# Copy the virtual environment from the builder stage
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy the configuration directory
COPY --chown=appuser:appuser config ./config

# Set the default command to show that the image works
CMD ["python", "-c", "print('Fume Hood Automation Docker image is ready. Use docker-compose to run services.')"] 