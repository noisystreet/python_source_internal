.PHONY: install lint format test clean docs

install:
	pip install -e ".[dev,lint,docs]"

lint:
	ruff check tests/ examples/
	mypy tests/

format:
	ruff format tests/ examples/

test:
	pytest

docs:
	python -m sphinx -b html docs docs/_build

clean:
	rm -rf build/ dist/ *.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete
	rm -rf .coverage htmlcov/ docs/_build/
