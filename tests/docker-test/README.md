# Docker Testing

Fast local testing with mocked hardware for development.

## Quick Start

```bash
# One-time setup
./tests/docker-test/scripts/setup_local_only.sh

# Quick integration test (recommended)
./tests/docker-test/scripts/test_local.sh integration

# If integration passes, run everything  
./tests/docker-test/scripts/test_local.sh all
```

## Test Types

| Test | What It Does | Speed | When to Use |
|------|--------------|-------|-------------|
| **integration** | Components working together | 5-10s | After code changes |
| **all** | Everything (unit + integration + E2E) | 30s | Before deployment |
| **unit** | Individual components only | 2-5s | Quick debugging |

## Workflow

```bash
# Daily development:
./tests/docker-test/scripts/test_local.sh integration    # Quick check

# Before pushing code:
./tests/docker-test/scripts/test_local.sh all           # Full validation
```

## Debugging

```bash
# Interactive shell for troubleshooting
./tests/docker-test/scripts/test_local.sh shell

# View test coverage
./tests/docker-test/scripts/test_local.sh coverage
open test-results/coverage/index.html
```

**Integration tests are usually enough** - they catch most issues without the overhead of full testing. 