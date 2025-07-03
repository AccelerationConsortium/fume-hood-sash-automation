#!/bin/bash
# scripts/run_tests.sh - Test execution script

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

# Create test results directory
mkdir -p test-results

# Function to run unit tests
run_unit_tests() {
    print_status "Running unit tests..."
    docker compose -f docker-test/dockerfiles/docker-compose.test.yml run --rm test-runner \
        pytest docker-test/tests/test_hall.py docker-test/tests/test_relay.py docker-test/tests/test_actuator_api.py -v
}

# Function to run integration tests
run_integration_tests() {
    print_status "Running integration tests..."
    docker compose -f docker-test/dockerfiles/docker-compose.test.yml run --rm test-runner \
        pytest docker-test/tests/test_integration_actuator.py -v
}

# Function to run end-to-end tests
run_e2e_tests() {
    print_status "Starting services for end-to-end testing..."
    
    # Start services in background
    docker compose -f docker-test/dockerfiles/docker-compose.test.yml up -d actuator-service sensor-service
    
    # Wait for services to be healthy
    print_status "Waiting for services to become healthy..."
    timeout=60
    elapsed=0
    while [ $elapsed -lt $timeout ]; do
        if docker compose -f docker-test/dockerfiles/docker-compose.test.yml ps | grep -q "healthy"; then
            break
        fi
        sleep 2
        elapsed=$((elapsed + 2))
    done
    
    if [ $elapsed -ge $timeout ]; then
        print_error "Services failed to become healthy within $timeout seconds"
        docker compose -f docker-test/dockerfiles/docker-compose.test.yml logs
        docker compose -f docker-test/dockerfiles/docker-compose.test.yml down
        exit 1
    fi
    
    print_success "Services are healthy, running end-to-end tests..."
    
    # Run E2E tests
    docker compose -f docker-test/dockerfiles/docker-compose.test.yml run --rm e2e-tests
    
    # Cleanup
    print_status "Cleaning up test services..."
    docker compose -f docker-test/dockerfiles/docker-compose.test.yml down
}

# Function to run all tests with coverage
run_all_tests() {
    print_status "Running complete test suite with coverage..."
    docker compose -f docker-test/dockerfiles/docker-compose.test.yml run --rm test-runner \
        pytest docker-test/tests/ --cov=src/hood_sash_automation \
        --cov-report=html:/app/test-results/coverage \
        --cov-report=term-missing \
        --cov-report=xml:/app/test-results/coverage.xml
}

# Function to run performance tests
run_performance_tests() {
    print_status "Running performance tests..."
    docker compose -f docker-test/dockerfiles/docker-compose.test.yml up -d actuator-service sensor-service
    
    # Wait for services
    sleep 10
    
    # Run basic load testing
    docker compose -f docker-test/dockerfiles/docker-compose.test.yml run --rm test-runner \
        python -c "
import requests
import time
import statistics

def load_test(url, num_requests=100):
    times = []
    errors = 0
    
    for i in range(num_requests):
        start = time.time()
        try:
            response = requests.get(url + '/status', timeout=5)
            if response.status_code == 200:
                times.append(time.time() - start)
            else:
                errors += 1
        except:
            errors += 1
    
    if times:
        print(f'URL: {url}')
        print(f'Requests: {num_requests}')
        print(f'Successful: {len(times)}')
        print(f'Errors: {errors}')
        print(f'Average response time: {statistics.mean(times):.3f}s')
        print(f'Min response time: {min(times):.3f}s')
        print(f'Max response time: {max(times):.3f}s')
        print('---')

load_test('http://actuator-service:5000')
load_test('http://sensor-service:5005')
"
    
    docker compose -f docker-test/dockerfiles/docker-compose.test.yml down
}

# Function to build test image
build_test_image() {
    print_status "Building test Docker image..."
    docker build -f docker-test/dockerfiles/Dockerfile.test -t fume-hood-test .
    print_success "Test image built successfully"
}

# Function to lint code
run_linting() {
    print_status "Running code linting..."
    docker run --rm -v "$(pwd)":/app -w /app fume-hood-test \
        python -m pylint src/hood_sash_automation/ --disable=import-error,no-member || true
}

# Function to check security
run_security_scan() {
    print_status "Running security scan..."
    docker run --rm -v "$(pwd)":/app -w /app fume-hood-test \
        python -m bandit -r src/ || true
}

# Function to clean up
cleanup() {
    print_status "Cleaning up Docker resources..."
    docker compose -f docker-test/dockerfiles/docker-compose.test.yml down -v
    docker system prune -f
    print_success "Cleanup completed"
}

# Main execution logic
case "${1:-all}" in
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
    "performance")
        build_test_image
        run_performance_tests
        ;;
    "coverage")
        build_test_image
        run_all_tests
        ;;
    "lint")
        build_test_image
        run_linting
        ;;
    "security")
        build_test_image
        run_security_scan
        ;;
    "all")
        build_test_image
        run_unit_tests
        run_integration_tests
        run_e2e_tests
        run_all_tests
        ;;
    "clean")
        cleanup
        ;;
    "help"|"-h"|"--help")
        echo "Usage: $0 [COMMAND]"
        echo ""
        echo "Commands:"
        echo "  unit         Run unit tests only"
        echo "  integration  Run integration tests only"
        echo "  e2e          Run end-to-end tests only"
        echo "  performance  Run performance tests"
        echo "  coverage     Run all tests with coverage report"
        echo "  lint         Run code linting"
        echo "  security     Run security scan"
        echo "  all          Run all tests (default)"
        echo "  clean        Clean up Docker resources"
        echo "  help         Show this help message"
        echo ""
        echo "Examples:"
        echo "  $0           # Run all tests"
        echo "  $0 unit      # Run only unit tests"
        echo "  $0 e2e       # Run only end-to-end tests"
        echo "  $0 coverage  # Run with coverage report"
        ;;
    *)
        print_error "Unknown command: $1"
        print_status "Use '$0 help' to see available commands"
        exit 1
        ;;
esac

print_success "Testing completed!" 