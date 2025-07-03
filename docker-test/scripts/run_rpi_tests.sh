#!/bin/bash
# scripts/run_tests_rpi.sh - Test execution script optimized for Raspberry Pi Zero W 2

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if running on Raspberry Pi
check_rpi_hardware() {
    if ! grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
        print_warning "Not running on Raspberry Pi hardware"
        read -p "Continue anyway? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        local model=$(grep "Model" /proc/cpuinfo | cut -d':' -f2 | xargs)
        print_status "Running on: $model"
    fi
}

# Check available memory (Pi Zero W 2 has limited RAM)
check_memory() {
    local mem_kb=$(grep MemTotal /proc/meminfo | awk '{print $2}')
    local mem_mb=$((mem_kb / 1024))
    print_status "Available memory: ${mem_mb}MB"
    
    if [ $mem_mb -lt 400 ]; then
        print_warning "Low memory detected. Tests may run slowly or fail."
        print_status "Consider closing other applications or running tests individually."
    fi
}

# Create test results directory
mkdir -p test-results

# Function to run unit tests (lightweight)
run_unit_tests() {
    print_status "Running unit tests on Raspberry Pi..."
    docker compose -f docker compose.test.rpi.yml run --rm test-runner \
        pytest docker-test/tests/test_hall.py docker-test/tests/test_relay.py docker-test/tests/test_actuator_api.py -v \
        --maxfail=3 --tb=short
}

# Function to run integration tests
run_integration_tests() {
    print_status "Running integration tests on Raspberry Pi..."
    docker compose -f docker compose.test.rpi.yml run --rm test-runner \
        pytest docker-test/tests/test_integration_actuator.py -v --maxfail=3 --tb=short
}

# Function to run end-to-end tests (with longer timeouts for Pi)
run_e2e_tests() {
    print_status "Starting services for end-to-end testing on Pi..."
    
    # Clean up any existing containers
    docker compose -f docker compose.test.rpi.yml down 2>/dev/null || true
    
    # Start services in background
    docker compose -f docker compose.test.rpi.yml up -d actuator-service sensor-service
    
    # Wait for services to be healthy (longer timeout for Pi)
    print_status "Waiting for services to become healthy (this may take longer on Pi)..."
    timeout=120  # Increased timeout for Pi Zero
    elapsed=0
    while [ $elapsed -lt $timeout ]; do
        if docker compose -f docker compose.test.rpi.yml ps | grep -q "healthy"; then
            break
        fi
        sleep 5
        elapsed=$((elapsed + 5))
        print_status "Still waiting... (${elapsed}s elapsed)"
    done
    
    if [ $elapsed -ge $timeout ]; then
        print_error "Services failed to become healthy within $timeout seconds"
        docker compose -f docker compose.test.rpi.yml logs
        docker compose -f docker compose.test.rpi.yml down
        exit 1
    fi
    
    print_success "Services are healthy, running end-to-end tests..."
    
    # Run E2E tests with Pi-specific settings
    docker compose -f docker compose.test.rpi.yml run --rm e2e-tests
    
    # Cleanup
    print_status "Cleaning up test services..."
    docker compose -f docker compose.test.rpi.yml down
}

# Function to run lightweight coverage (reduced scope for Pi)
run_coverage_tests() {
    print_status "Running lightweight test coverage on Pi..."
    docker compose -f docker compose.test.rpi.yml run --rm test-runner \
        pytest docker-test/tests/test_hall.py docker-test/tests/test_relay.py docker-test/tests/test_actuator_api.py \
        --cov=src/hood_sash_automation/actuator \
        --cov-report=term-missing \
        --cov-report=html:/app/test-results/coverage
}

# Function to build test image for Pi
build_test_image() {
    print_status "Building test Docker image for Raspberry Pi..."
    print_warning "This may take several minutes on Pi Zero W 2..."
    
    # Enable BuildKit for better performance
    export DOCKER_BUILDKIT=1
    docker build -f docker-test/dockerfiles/Dockerfile.test -t fume-hood-test:rpi .
    print_success "Test image built successfully"
}

# Function to run hardware-specific tests
run_hardware_tests() {
    print_status "Running hardware-specific tests..."
    
    # Check if GPIO is accessible
    if [ -e /dev/gpiomem ]; then
        print_success "GPIO device found"
    else
        print_warning "GPIO device not found - hardware tests may fail"
    fi
    
    # Check if I2C is accessible
    if [ -e /dev/i2c-1 ]; then
        print_success "I2C device found"
    else
        print_warning "I2C device not found - sensor tests may fail"
    fi
    
    # Run tests with actual hardware access
    docker compose -f docker compose.rpi.yml run --rm actuator \
        python -c "
import sys
sys.path.append('/app/src')
try:
    from hood_sash_automation.actuator.controller import SashActuator
    print('✓ Actuator imports work')
except Exception as e:
    print(f'✗ Actuator import failed: {e}')

try:
    import RPi.GPIO as GPIO
    print('✓ RPi.GPIO is available')
except Exception as e:
    print(f'✗ RPi.GPIO not available: {e}')
"
}

# Function to monitor system resources
monitor_resources() {
    print_status "System resource usage:"
    echo "Memory usage:"
    free -h
    echo ""
    echo "CPU temperature:"
    vcgencmd measure_temp 2>/dev/null || echo "Temperature monitoring not available"
    echo ""
    echo "Disk usage:"
    df -h / | tail -1
}

# Function to clean up
cleanup() {
    print_status "Cleaning up Docker resources on Pi..."
    docker compose -f docker compose.test.rpi.yml down -v 2>/dev/null || true
    docker compose -f docker compose.rpi.yml down -v 2>/dev/null || true
    
    # More aggressive cleanup for Pi Zero (limited storage)
    print_status "Pruning Docker system..."
    docker system prune -f
    docker image prune -f
    
    print_success "Cleanup completed"
}

# Pi-specific optimizations
optimize_for_pi() {
    # Increase swap if needed (for builds)
    local swap_size=$(swapon -s | tail -n +2 | awk '{sum += $3} END {print sum}')
    if [ -z "$swap_size" ] || [ "$swap_size" -lt 512000 ]; then
        print_warning "Low or no swap detected. Consider increasing swap for Docker builds."
    fi
    
    # Set Docker memory limits
    export COMPOSE_MEMORY_LIMIT=150m
}

# Main execution logic
main() {
    print_status "Raspberry Pi Fume Hood Test Runner"
    print_status "=================================="
    
    check_rpi_hardware
    check_memory
    optimize_for_pi
    
    case "${1:-help}" in
        "unit")
            build_test_image
            run_unit_tests
            ;;
        "integration")
            build_test_image
            run_integration_tests
            ;;
        "e2e")
            build_test_image
            run_e2e_tests
            ;;
        "coverage")
            build_test_image
            run_coverage_tests
            ;;
        "hardware")
            run_hardware_tests
            ;;
        "monitor")
            monitor_resources
            ;;
        "build")
            build_test_image
            ;;
        "quick")
            print_status "Running quick test suite for Pi..."
            build_test_image
            run_unit_tests
            run_coverage_tests
            ;;
        "clean")
            cleanup
            ;;
        "help"|"-h"|"--help")
            echo "Usage: $0 [COMMAND]"
            echo ""
            echo "Raspberry Pi Zero W 2 Optimized Commands:"
            echo "  unit         Run unit tests only (lightweight)"
            echo "  integration  Run integration tests"
            echo "  e2e          Run end-to-end tests (with longer timeouts)"
            echo "  coverage     Run lightweight coverage report"
            echo "  hardware     Test hardware access and imports"
            echo "  monitor      Show system resource usage"
            echo "  build        Build test image only"
            echo "  quick        Run essential tests quickly"
            echo "  clean        Clean up Docker resources"
            echo "  help         Show this help message"
            echo ""
            echo "Pi-specific optimizations:"
            echo "  - Uses ARM-compatible Docker images"
            echo "  - Memory-limited containers"
            echo "  - Extended timeouts for slower hardware"
            echo "  - Hardware device mounting for GPIO/I2C"
            echo ""
            ;;
        *)
            print_error "Unknown command: $1"
            print_status "Use '$0 help' to see available commands"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"

if [ $? -eq 0 ]; then
    print_success "Testing completed successfully!"
    monitor_resources
else
    print_error "Testing failed!"
    exit 1
fi 