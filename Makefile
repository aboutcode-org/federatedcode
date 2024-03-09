# SPDX-License-Identifier: Apache-2.0
#
# Copyright (c) nexB Inc. and others. All rights reserved.
# ScanCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/skeleton for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#
include .env

# Python version can be specified with `$ PYTHON_EXE=python3.x make conf`
PYTHON_EXE?=python3
VENV=venv
ACTIVATE?=. ${VENV}/bin/activate;
MANAGE=${VENV}/bin/python manage.py

# Use sudo for postgres, but only on Linux
UNAME := $(shell uname)
ifeq ($(UNAME), Linux)
	SUDO_POSTGRES=sudo -u postgres
else
	SUDO_POSTGRES=
endif

dev:
	@echo "-> Configure the development envt."
	./configure --dev

envfile:
	@echo "-> Create the .env file and generate a secret key"
	@if test -f ${ENV_FILE}; then echo ".env file exists already"; exit 1; fi
	@mkdir -p $(shell dirname ${ENV_FILE}) && touch ${ENV_FILE}
	@echo SECRET_KEY=\"${GET_SECRET_KEY}\" > ${ENV_FILE}

isort:
	@echo "-> Apply isort changes to ensure proper imports ordering"
	${VENV}/bin/isort --sl -l 100 tests setup.py

black:
	@echo "-> Apply black code formatter"
	${VENV}/bin/black -l 100 tests setup.py

doc8:
	@echo "-> Run doc8 validation"
	@${ACTIVATE} doc8 --max-line-length 100 --ignore-path docs/_build/ --quiet docs/

valid: isort black

check:
	@echo "-> Run pycodestyle (PEP8) validation"
	@${ACTIVATE} pycodestyle --max-line-length=100 --exclude=.eggs,venv,lib,thirdparty,docs,migrations,settings.py,.cache .
	@echo "-> Run isort imports ordering validation"
	@${ACTIVATE} isort --sl --check-only -l 100 setup.py tests .
	@echo "-> Run black validation"
	@${ACTIVATE} black --check --check -l 100 tests setup.py

clean:
	@echo "-> Clean the Python env"
	./configure --clean

test:
	@echo "-> Run the test suite"
	${VENV}/bin/pytest -vvs

docs:
	rm -rf docs/_build/
	@${ACTIVATE} sphinx-build docs/source docs/_build/


postgres:
	@echo "-> Configure PostgreSQL database"
	@echo "-> Create database user '${POSTGRES_DB}'"
	${SUDO_POSTGRES} createuser --no-createrole --no-superuser --login --inherit --createdb ${POSTGRES_DB} || true
	${SUDO_POSTGRES} psql -c "alter user ${POSTGRES_USER} with encrypted password '${POSTGRES_PASSWORD}';" || true
	@echo "-> Drop '${POSTGRES_DB}' database"
	${SUDO_POSTGRES} dropdb ${POSTGRES_DB} || true
	@echo "-> Create '${POSTGRES_DB}' database"
	${SUDO_POSTGRES} createdb --encoding=utf-8 --owner=${POSTGRES_USER} ${POSTGRES_DB}
	@$(MAKE) migrate

migrate:
	@echo "-> Apply database migrations"
	${MANAGE} migrate

.PHONY: conf dev check valid black isort clean test docs envfile postgres migrate
