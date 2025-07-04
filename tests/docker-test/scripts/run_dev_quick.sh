#!/bin/bash
# run_dev_quick.sh - Fast development testing with volume mounts
# No rebuilds needed - uses existing image with mounted source code

set -e
cd "$(dirname "$0")/../.."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Fast Development Testing (Volume Mounted)${NC}"
echo "================================================"

# Build image only once if it doesn't exist
if ! docker image inspect fume-hood-test:latest >/dev/null 2>&1; then
    echo -e "${YELLOW}📦 Building base test image (one-time setup)...${NC}"
    docker build -f docker-test/dockerfiles/Dockerfile.test -t fume-hood-test:latest .
    echo -e "${GREEN}✅ Base image built${NC}"
else
    echo -e "${GREEN}✅ Using existing base image${NC}"
fi

# Function to run tests quickly
run_quick_test() {
    local test_type="$1"
    local test_files="$2"
    
    echo -e "${BLUE}🧪 Running $test_type tests...${NC}"
    docker run --rm \
        -v "$(pwd):/app:cached" \
        -v "$(pwd)/test-results:/app/test-results" \
        -w /app \
        -e PYTHONPATH="/app/docker-test/mock_hardware:/app/src" \
        -e FLASK_ENV=testing \
        fume-hood-test:latest \
        pytest $test_files -v --tb=short
}

# Function to start services for E2E testing
start_dev_services() {
    echo -e "${BLUE}🏗️ Starting development services...${NC}"
    docker compose -f docker-test/dockerfiles/docker-compose.dev.yml up -d dev-actuator dev-sensor
    
    # Wait for services
    echo -e "${YELLOW}⏳ Waiting for services to be ready...${NC}"
    sleep 5
    
    # Check if services are healthy
    if curl -f http://localhost:5000/status >/dev/null 2>&1 && \
       curl -f http://localhost:5005/status >/dev/null 2>&1; then
        echo -e "${GREEN}✅ Services are ready${NC}"
        return 0
    else
        echo -e "${RED}❌ Services failed to start${NC}"
        docker compose -f docker-test/dockerfiles/docker-compose.dev.yml logs
        return 1
    fi
}

# Function to stop services
stop_dev_services() {
    echo -e "${YELLOW}🛑 Stopping development services...${NC}"
    docker compose -f docker-test/dockerfiles/docker-compose.dev.yml down
}

# Parse command line arguments
case "${1:-all}" in
    "unit")
        run_quick_test "unit" "docker-test/tests/test_hall.py docker-test/tests/test_relay.py docker-test/tests/test_actuator_api.py"
        ;;
    "integration")
        run_quick_test "integration" "docker-test/tests/test_integration_actuator.py docker-test/tests/test_actuator_controller.py"
        ;;
    "e2e")
        start_dev_services
        if [ $? -eq 0 ]; then
            run_quick_test "E2E" "docker-test/tests/test_e2e_api.py"
        fi
        stop_dev_services
        ;;
    "shell")
        echo -e "${BLUE}🐚 Starting interactive shell in test container...${NC}"
        docker run -it --rm \
            -v "$(pwd):/app:cached" \
            -w /app \
            -e PYTHONPATH="/app/docker-test/mock_hardware:/app/src" \
            -e FLASK_ENV=testing \
            fume-hood-test:latest \
            bash
        ;;
    "services")
        start_dev_services
        echo -e "${GREEN}✅ Services running. Access:${NC}"
        echo -e "   Actuator API: ${BLUE}http://localhost:5000${NC}"
        echo -e "   Sensor API:   ${BLUE}http://localhost:5005${NC}"
        echo -e "${YELLOW}Press Ctrl+C to stop services${NC}"
        trap stop_dev_services SIGINT SIGTERM
        
        # Keep script running until interrupted
        while true; do
            sleep 1
        done
        ;;
    "all"|*)
        echo -e "${BLUE}🧪 Running all tests...${NC}"
        run_quick_test "unit" "docker-test/tests/test_hall.py docker-test/tests/test_relay.py docker-test/tests/test_actuator_api.py"
        run_quick_test "integration" "docker-test/tests/test_integration_actuator.py docker-test/tests/test_actuator_controller.py"
        
        start_dev_services
        if [ $? -eq 0 ]; then
            run_quick_test "E2E" "docker-test/tests/test_e2e_api.py"
        fi
        stop_dev_services
        ;;
esac

echo -e "${GREEN}✅ Testing complete!${NC}" 