# This line is setting a variable ROOT_DIR to the absolute path of the directory where the Makefile is located.
ROOT_DIR := $(dir $(realpath $(lastword $(MAKEFILE_LIST))))
# The purpose of this command is to extract lines from .gitignore that are between # Clean and # End Clean comments
CLEAN_PATTERNS := $(shell grep -A 1000 "# Clean" .gitignore | grep -B 1000 "# End Clean" | grep -v "^#")


.PHONY: clean
clean:
	@$(foreach pattern,$(CLEAN_PATTERNS), \
		find . -name "$(pattern)" -exec rm -rf {} +; \
	)

install:
	poetry run bash auto_dev/data/repo/templates/autonomy/install.sh
lint:
	poetry run adev -v -n 0 lint -p . -co

fmt: 
	poetry run adev -n 0 fmt -p . -co

test:
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
