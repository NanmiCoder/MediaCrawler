.PHONY: install-dev test test-unit clean

# Install development and test dependencies (requirements-based, no editable install)
install-dev:
	pip install -r requirements.txt
	pip install -r requirements-test.txt
	pip install -r api/requirements.txt

# Run full regression test suite
test:
	pytest douyin_scraper/tests/ -q
	pytest api/tests.py -q

# Run unit tests only (skip integration)
test-unit:
	pytest douyin_scraper/tests/ -q -k "not integration"

# Clean build artifacts
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .mypy_cache htmlcov .coverage
