install:
	poetry run bash auto_dev/data/repo/templates/autonomy/install.sh
lint:
	poetry run adev -v -n 0 lint -p . -co

fmt: 
	poetry run adev -n 0 fmt -p . -co

test:
	poetry run adev -v test -p tests

docs:
	poetry run mkdocs build

all: fmt lint test

submit: install fmt lint test
	date=$(shell date) && git add . && git commit -m "Auto commit at $(date)" && git push

dev:
	echo 'Starting dev mode...'
	poetry run bash scripts/dev.sh
