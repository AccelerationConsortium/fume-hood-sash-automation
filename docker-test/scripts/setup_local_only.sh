#!/bin/bash
# setup_local_only.sh - Set up persistent local testing (no CI/CD)

set -e
cd "$(dirname "$0")/../.."

echo "🏠 Setting up LOCAL-ONLY testing environment"
echo "=============================================="

# Build base test image once
echo "📦 Building base test image..."
docker build -f docker-test/dockerfiles/Dockerfile.test -t fume-hood-test:latest .

# Start persistent test container (no ports needed for testing)
echo "🚀 Starting persistent test container..."
docker run -d \
    --name fume-hood-dev \
    -v "$(pwd):/app:cached" \
    -v "$(pwd)/test-results:/app/test-results" \
    -w /app \
    -e PYTHONPATH="/app/docker-test/mock_hardware:/app/src" \
    -e FLASK_ENV=testing \
    fume-hood-test:latest \
    tail -f /dev/null

echo "✅ Persistent container 'fume-hood-dev' is running!"
echo ""
echo "🧪 Quick test commands:"
echo "  docker exec fume-hood-dev pytest docker-test/tests/test_hall.py -v"
echo "  docker exec fume-hood-dev pytest docker-test/tests/ --cov=src/hood_sash_automation"
echo ""
echo "🐚 Interactive shell:"
echo "  docker exec -it fume-hood-dev bash"
echo ""
echo "🛑 To stop:"
echo "  docker stop fume-hood-dev && docker rm fume-hood-dev" 