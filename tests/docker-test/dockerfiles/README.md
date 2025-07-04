# Docker Testing Infrastructure

This directory contains all Docker-related files for testing the Fume Hood Sash Automation project on Raspberry Pi Zero 2W.

## File Structure

```
test/docker/
├── README.md                          # This file
├── Dockerfile                         # Production Docker image (Pi-optimized)
├── Dockerfile.test                    # Testing Docker image with test dependencies
├── docker-compose.yml                 # Original production compose file
├── docker-compose.rpi.yml            # Pi Zero 2W optimized production
├── docker-compose.test.yml           # Development/x86 testing
└── docker-compose.test.rpi.yml       # Pi Zero 2W optimized testing
```

## Docker Images

### **Production Images**
- **`Dockerfile`**: Official Raspberry Pi OS base image with Python 3.9
- **Base**: `dtcooper/raspberrypi-os:python3.9-bullseye`
- **Features**: RPi.GPIO, Pi-specific packages, multi-arch support

### **Test Images** 
- **`Dockerfile.test`**: Same base + testing dependencies
- **Additional packages**: pytest, coverage, requests, etc.
- **Purpose**: Unit, integration, and E2E testing

## Docker Compose Files

### **Production Deployment**
- **`docker-compose.rpi.yml`**: Pi Zero 2W production deployment
  - GPIO/I2C device mounting
  - Memory limits (512MB total Pi RAM)
  - Hardware privilege access
  - Auto-restart policies

### **Testing Environments**
- **`docker-compose.test.yml`**: Development testing (x86/ARM)
- **`docker-compose.test.rpi.yml`**: Pi-specific testing
  - Extended timeouts for Pi hardware
  - Resource constraints
  - Mock hardware for testing

## Usage

### **From Project Root**

#### **Development Testing** (Mac/x86)
```bash
# Quick unit tests
./scripts/run_tests.sh unit

# Full test suite with coverage
./scripts/run_tests.sh coverage

# End-to-end testing
./scripts/run_tests.sh e2e
```

#### **Pi Zero 2W Testing**
```bash
# Essential tests (recommended for Pi)
./scripts/run_tests_rpi.sh quick

# Hardware validation
./scripts/run_tests_rpi.sh hardware

# System monitoring
./scripts/run_tests_rpi.sh monitor
```

#### **Production Deployment** (on Pi)
```bash
# Deploy services
docker compose -f test/docker/docker-compose.rpi.yml up -d

# Check status
docker compose -f test/docker/docker-compose.rpi.yml ps

# View logs
docker compose -f test/docker/docker-compose.rpi.yml logs
```

## Build Process

All Docker builds use the **project root** as build context:
```bash
# Build from project root (not from test/docker/)
cd /path/to/fume-hood-sash-automation
docker build -f test/docker/Dockerfile.test -t fume-hood-test .
```

This allows Dockerfiles to copy from:
- `src/` - Application source code
- `tests/` - Test files  
- `users/config/` - Configuration files
- `pyproject.toml` - Dependencies

## Architecture Support

- **Primary**: ARM64 (64-bit) for Pi Zero 2W
- **Secondary**: ARM32 (32-bit) compatibility
- **Development**: x86_64 (Intel/AMD) on macOS/Linux

The `dtcooper/raspberrypi-os` images automatically select the appropriate architecture for your target platform.

## Memory Optimization

### **Pi Zero 2W Limits** (512MB total RAM)
- **Actuator Service**: 200MB limit, 100MB reserved
- **Sensor Service**: 150MB limit, 75MB reserved
- **Test Containers**: 150MB limit, 100MB reserved

### **Development** (Unlimited)
- No memory constraints
- Faster execution
- Full feature testing

## Hardware Integration

### **GPIO Access** (Pi only)
```yaml
volumes:
  - /dev/gpiomem:/dev/gpiomem
devices:  
  - /dev/gpiomem:/dev/gpiomem
privileged: true
```

### **I2C Access** (Pi only)  
```yaml
volumes:
  - /dev/i2c-1:/dev/i2c-1
devices:
  - /dev/i2c-1:/dev/i2c-1
```

### **Mock Hardware** (Testing)
```yaml
volumes:
  - /dev/null:/dev/gpiomem  # Mock GPIO
  - /dev/null:/dev/i2c-1    # Mock I2C
```

## Troubleshooting

### **Build Issues**
```bash
# Enable Docker BuildKit (faster builds)
export DOCKER_BUILDKIT=1

# Clean build (no cache)
docker build --no-cache -f test/docker/Dockerfile.test .

# Check available space
docker system df
```

### **Pi Performance**
```bash
# Monitor resources during testing
./scripts/run_tests_rpi.sh monitor

# Increase swap if needed
sudo dphys-swapfile swapoff
sudo nano /etc/dphys-swapfile  # Set CONF_SWAPSIZE=1024
sudo dphys-swapfile setup && sudo dphys-swapfile swapon
```

### **Permission Issues**
```bash
# Add user to docker group
sudo usermod -aG docker $USER

# Add user to gpio/i2c groups (Pi only)
sudo usermod -aG gpio,i2c $USER
```

## CI/CD Integration

The `.github/workflows/test.yml` automatically:
- Builds multi-architecture images
- Runs parallel test suites
- Generates coverage reports
- Performs security scanning
- Uploads test artifacts

 