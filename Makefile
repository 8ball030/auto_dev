
.PHONY: clean
clean: clean-build clean-pyc clean-test clean-docs

.PHONY: clean-build
clean-build:
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	rm -fr deployments/build/
	rm -fr deployments/Dockerfiles/open_aea/packages
	rm -fr pip-wheel-metadata
	find packages -name '*.egg-info' -exec rm -fr {} +
	find packages -name '*.egg' -exec rm -fr {} +
	find packages -name '*.svn' -exec rm -fr {} +
	find packages -name '*.db' -exec rm -fr {} +
	rm -fr .idea .history
	rm -fr venv

.PHONY: clean-docs
clean-docs:
	rm -fr site/

.PHONY: clean-pyc
clean-pyc:
	find packages -name '*.pyc' -exec rm -f {} +
	find packages -name '*.pyo' -exec rm -f {} +
	find packages -name '__pycache__' -exec rm -fr {} +

.PHONY: clean-test
clean-test:
	rm -fr .tox/
	rm -f .coverage
	find packages -name ".coverage*" -not -name ".coveragerc" -exec rm -fr "{}" \;
	rm -fr coverage.xml
	rm -fr htmlcov/
	rm -fr .hypothesis
	rm -fr .pytest_cache
	rm -fr .mypy_cache/
	find packages -name 'log.txt' -exec rm -fr {} +
	find packages -name 'log.*.txt' -exec rm -fr {} +

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
