.PHONY: install test build clean run help

PYTHON = python
VENV = venv
PIP = $(VENV)/bin/pip
PYTHON_VENV = $(VENV)/bin/python

help:  ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: $(VENV)/bin/activate  ## Install dependencies in virtual environment

$(VENV)/bin/activate: requirements.txt
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	touch $(VENV)/bin/activate

test: install  ## Run tests
	$(PYTHON_VENV) -m pytest tests/ -v

run: install  ## Run the application
	$(PYTHON_VENV) -m src/main.py

build: install test  ## Build executable for current platform
	$(PYTHON_VENV) build_spec.py

build-windows:  ## Build Windows executable (cross-platform)
	docker run --rm -v $(PWD):/app -w /app python:3.11-windowsservercore \
		powershell -Command "pip install -r requirements.txt; python build_spec.py"

build-linux:  ## Build Linux executable (cross-platform)
	docker run --rm -v $(PWD):/app -w /app python:3.11-slim \
		bash -c "apt-get update && apt-get install -y build-essential && pip install -r requirements.txt && python build_spec.py"

clean:  ## Clean build artifacts and virtual environment
	rm -rf $(VENV)
	rm -rf build/
	rm -rf dist/
	rm -rf *.spec
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete

lint: install  ## Run code linting
	$(PIP) install flake8 black isort
	$(PYTHON_VENV) -m flake8 src/ tests/
	$(PYTHON_VENV) -m black --check src/ tests/
	$(PYTHON_VENV) -m isort --check-only src/ tests/

format: install  ## Format code
	$(PIP) install black isort
	$(PYTHON_VENV) -m black src/ tests/
	$(PYTHON_VENV) -m isort src/ tests/

dev-install: install  ## Install development dependencies
	$(PIP) install -r requirements.txt
	$(PIP) install pytest pytest-qt flake8 black isort

package: build  ## Create distribution packages
	mkdir -p dist/packages
	tar -czf dist/packages/dps-clip-tracker-linux.tar.gz -C dist DPSClipTracker
	zip -j dist/packages/dps-clip-tracker-windows.zip dist/DPSClipTracker.exe