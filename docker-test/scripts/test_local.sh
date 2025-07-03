#!/bin/bash
# test_local.sh - Run tests in persistent local container

CONTAINER_NAME="fume-hood-dev"

# Check if container exists and is running
if ! docker ps | grep -q "$CONTAINER_NAME"; then
    echo "❌ Container '$CONTAINER_NAME' not running!"
    echo "Run: ./docker-test/scripts/setup_local_only.sh"
    exit 1
fi

case "${1:-all}" in
    "unit")
        echo "🧪 Running unit tests..."
        docker exec $CONTAINER_NAME pytest docker-test/tests/test_hall.py docker-test/tests/test_relay.py docker-test/tests/test_actuator_api.py -v
        ;;
    "integration") 
        echo "🔗 Running integration tests..."
        docker exec $CONTAINER_NAME pytest docker-test/tests/test_integration_actuator.py docker-test/tests/test_actuator_controller.py -v
        ;;
    "coverage")
        echo "📊 Running coverage analysis..."
        docker exec $CONTAINER_NAME pytest docker-test/tests/ --cov=src/hood_sash_automation --cov-report=term-missing --cov-report=html:/app/test-results/coverage
        ;;
    "shell")
        echo "🐚 Opening interactive shell..."
        docker exec -it $CONTAINER_NAME bash
        ;;
    "all"|*)
        echo "🧪 Running all tests..."
        docker exec $CONTAINER_NAME pytest docker-test/tests/ -v --cov=src/hood_sash_automation --cov-report=term-missing
        ;;
esac 