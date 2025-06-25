# Dockerfile for fume-hood-sash-automation

# --- Stage 1: Builder ---
# This stage installs all dependencies, including test and mock libraries,
# and builds the package.
FROM python:3.9-slim-bullseye AS builder

WORKDIR /app

# Install system dependencies that might be needed by Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install mock libraries needed for running on a non-Pi system
# We are installing these separately because they should not be part of the main package dependencies.
RUN pip install fake-rpigpio smbus2-mocks

# Copy project files
COPY pyproject.toml README.md ./
COPY src ./src

# Install the project with all its dependencies.
# The mock libraries we installed above will satisfy the hardware requirements.
RUN pip install .[actuator,sensor]


# --- Stage 2: Final ---
# This stage creates the final, lean image. It copies the installed
# application from the builder stage, but not the build tools or extra libraries.
FROM python:3.9-slim-bullseye

WORKDIR /app

# Create a non-root user to run the application for better security
RUN useradd --create-home appuser
USER appuser

# Copy the virtual environment from the builder stage
COPY --from=builder /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy the configuration directory
COPY --chown=appuser:appuser config ./config

# Set the default command to show that the image works
CMD ["python", "-c", "print('Fume Hood Automation Docker image is ready. Use docker-compose to run services.')"] 