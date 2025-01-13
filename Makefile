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
	poetry run mkdocs build

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
