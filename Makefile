# This line is setting a variable ROOT_DIR to the absolute path of the directory where the Makefile is located.
ROOT_DIR := $(dir $(realpath $(lastword $(MAKEFILE_LIST))))
# The purpose of this command is to extract lines from .gitignore that are between # Clean and # End Clean comments
CLEAN_PATTERNS = $(shell sed -n '/^# Clean$$/,/^# End Clean$$/p' .gitignore)

.PHONY: clean
clean:
	@$(foreach pattern,$(CLEAN_PATTERNS), \
		find . -name "$(pattern)" -exec rm -rf {} +; \
	)

install:
	poetry run bash auto_dev/data/repo/templates/autonomy/install.sh
	make update_protocol_tests

lint:
	poetry run adev -v -n 0 lint -p . -co

fmt:
	poetry run adev -n 0 fmt -p . -co

test:
	make update_protocol_tests
	poetry run adev -v test -p tests

.PHONY: docs
docs:
	poetry run python scripts/generate_command_docs.py && poetry run mkdocs build

docs-serve:
	poetry run mkdocs serve

all: fmt lint test

submit: install fmt lint test
	date=$(shell date) && git add . && git commit -m "Auto commit at $(date)" && git push

dev:
	echo 'Starting dev mode...'
	poetry run bash scripts/dev.sh

new_env:
	git pull
	poetry env remove --all
	make install


PROTOCOLS_URL = https://github.com/StationsStation/capitalisation_station/archive/main.zip
PROTOCOLS_DIR = ${ROOT_DIR}tests/data/protocols/.capitalisation_station
TEMP_ZIP = .capitalisation_station.zip

update_protocol_tests:
	@echo "Downloading protocol specification for testing..."
	@curl -L $(PROTOCOLS_URL) -o $(TEMP_ZIP)
	@echo "Extracting protocol specification..."
	@mkdir -p $(PROTOCOLS_DIR)
	@unzip -q $(TEMP_ZIP) "capitalisation_station-main/specs/protocols/*" -d .tmp_protocols
	@mv .tmp_protocols/capitalisation_station-main/specs/protocols/* $(PROTOCOLS_DIR)/
	@rm -rf .tmp_protocols $(TEMP_ZIP)
	@echo "Protocols updated in $(PROTOCOLS_DIR)"
