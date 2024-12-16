PYTHON_CMD = python3
VENV_DIR = venv
REQUIREMENTS = requirements.txt
MINION_C_SOURCE = minion.c
MINION_OUTPUT = a.out
PROGEN_PY = ProGen.py
PYINSTALLER = pyinstaller
DIST_DIR = dist
BUILD_DIR = build
COMPILED_PROGEN = ProGen

# Ensure Python >= 3.9 is installed
check_python:
	@echo "Checking for Python >= 3.9..."
	@if ! command -v $(PYTHON_CMD) > /dev/null; then \
		echo "Python is not installed."; \
		exit 1; \
	fi
	@if ! $(PYTHON_CMD) -c 'import sys; assert sys.version_info >= (3, 9)' > /dev/null 2>&1; then \
		echo "Python version must be >= 3.9"; \
		exit 1; \
	fi
	@echo "Python is ready."

# Ensure pip is installed
check_pip:
	@echo "Checking for pip..."
	@if ! $(PYTHON_CMD) -m pip --version > /dev/null 2>&1; then \
		echo "pip is not installed."; \
		$(PYTHON_CMD) -m ensurepip; \
	fi
	@echo "pip is ready."

# Ensure virtualenv is installed
check_venv:
	@echo "Checking for virtualenv..."
	@if ! $(PYTHON_CMD) -m venv --help > /dev/null 2>&1; then \
		echo "Virtualenv is not installed."; \
		$(PYTHON_CMD) -m pip install --upgrade virtualenv; \
	fi
	@echo "Virtualenv is ready."

# Create a virtual environment
create_venv: check_python check_pip check_venv
	@echo "Creating virtual environment..."
	@$(PYTHON_CMD) -m venv $(VENV_DIR)
	@echo "Virtual environment created."

# Install dependencies from requirements.txt
install_requirements: create_venv
	@echo "Installing requirements from $(REQUIREMENTS)..."
	@$(VENV_DIR)/bin/pip install -r $(REQUIREMENTS)
	@echo "Requirements installed."

# Ensure GCC is installed
check_gcc:
	@echo "Checking for GCC..."
	@if ! command -v gcc > /dev/null 2>&1; then \
		echo "GCC is not installed."; \
		exit 1; \
	fi
	@echo "GCC is ready."

# Compile minion.c with GCC
compile_minion: check_gcc
	@echo "Compiling $(MINION_C_SOURCE)..."
	@gcc $(MINION_C_SOURCE) -o $(MINION_OUTPUT)
	@echo "Compilation completed: $(MINION_OUTPUT)"

# Run ProGen.py using the virtual environment
run_progen: install_requirements compile_minion
	@echo "Running $(PROGEN_PY) using virtual environment..."
	@$(VENV_DIR)/bin/python $(PROGEN_PY)

compile_progen: install_requirements compile_minion
	@echo "Compiling $(PROGEN_PY) using pyinstaller..."
	@$(PYINSTALLER) --onefile $(PROGEN_PY)

run_compiled_progen: compile_progen
	@$(DIST_DIR)/$(COMPILED_PROGEN)

# Clean up the environment
clean:
	@echo "Cleaning up..."
	@rm -rf $(VENV_DIR)
	@rm -f $(MINION_OUTPUT)
	@rm -rf $(DIST_DIR)
	@rm -rf $(BUILD_DIR)
	@echo "Clean up complete."

# Default target
all: run_progen

compiled: run_compiled_progen

.DEFAULT_GOAL := all

