.PHONY: install-dev test test-core test-baseline test-all test-known-failures test-external test-unit clean

# Install development and test dependencies (requirements-based, no editable install)
install-dev:
	pip install -r requirements.txt
	pip install -r requirements-test.txt
	pip install -r api/requirements.txt

# Stable merge-gate regression suite
test: test-core

test-core:
	pytest douyin_scraper/tests/ -q
	pytest api/tests.py -q

# Legacy baseline; a non-zero exit is expected while known failures remain
test-baseline:
	pytest tests/ test/ -q

# Complete repository suite with external integrations skipped by default
test-all:
	pytest douyin_scraper/tests/ api/tests.py tests/ test/ -q

# Run the tracked T021 known failures without converting them to xfail
test-known-failures:
	pytest tests/ test/ -m known_fail -q

# Opt in to Redis, MongoDB, and real proxy-provider integration tests
test-external:
	MEDIACRAWLER_RUN_EXTERNAL_TESTS=1 pytest test/ -m external -q

# Run unit tests only (skip integration)
test-unit:
	pytest douyin_scraper/tests/ -q

# Clean build artifacts
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .mypy_cache htmlcov .coverage
