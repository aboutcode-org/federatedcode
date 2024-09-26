#
# Copyright (c) nexB Inc. and others. All rights reserved.
# FederatedCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See https://github.com/nexB/federatedcode for support or download.
# See https://aboutcode.org for more information about AboutCode FOSS projects.
#
# include .env

# Python version can be specified with `$ PYTHON_EXE=python3.x make conf`
PYTHON_EXE?=python3
VENV=venv
MANAGE=${VENV}/bin/python manage.py
ACTIVATE?=. ${VENV}/bin/activate;
MANAGE=${VENV}/bin/python manage.py
BLACK_ARGS=--exclude=".cache|migrations|data|venv|lib|bin|var|etc"

# Do not depend on Python to generate the SECRET_KEY and other ids
GET_SECRET_KEY=`base64 /dev/urandom | head -c50`
GET_FEDERATEDCODE_CLIENT_ID=`base64 /dev/urandom | head -c40`
GET_FEDERATEDCODE_CLIENT_SECRET=`base64 /dev/urandom | head -c128`


# Customize with `$ make envfile ENV_FILE=/etc/federatedcode/.env`
ENV_FILE=.env
# Customize with `$ make postgres FEDERATEDCODE_DB_PASSWORD=YOUR_PASSWORD`
FEDERATEDCODE_DB_NAME=federatedcode
FEDERATEDCODE_DB_USER=federatedcode
FEDERATEDCODE_DB_PASSWORD=federatedcode
POSTGRES_INITDB_ARGS=--encoding=UTF-8 --lc-collate=en_US.UTF-8 --lc-ctype=en_US.UTF-8
DATE=$(shell date +"%Y-%m-%d_%H%M")

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
	@echo "-> Create the .env file and generate secret keys and client id"
	@if test -f ${ENV_FILE}; then echo ".env file exists already"; exit 1; fi
	@mkdir -p $(shell dirname ${ENV_FILE}) && touch ${ENV_FILE}
	@echo SECRET_KEY=\"${GET_SECRET_KEY}\" >> ${ENV_FILE}
	@echo FEDERATEDCODE_CLIENT_ID=\"${GET_FEDERATEDCODE_CLIENT_ID}\" >> ${ENV_FILE}
	@echo FEDERATEDCODE_CLIENT_SECRET=\"${GET_FEDERATEDCODE_CLIENT_SECRET}\" >> ${ENV_FILE}

isort:
	@echo "-> Apply isort changes to ensure proper imports ordering"
	@${ACTIVATE} isort --profile black .

black:
	@echo "-> Apply black code formatter"
	@${ACTIVATE} black ${BLACK_ARGS} .

doc8:
	@echo "-> Run doc8 validation"
	@${ACTIVATE} doc8 --max-line-length 100 --ignore-path docs/_build/ --quiet docs/

valid: isort black doc8

bandit:
	@echo "-> Run source code security analyzer"
	@${ACTIVATE} bandit -r fedcode federatedcode --quiet

check: doc8 bandit
	@echo "-> Run flake8 (pycodestyle, pyflakes, mccabe) validation"
	@${ACTIVATE} flake8 .
	@echo "-> Run isort imports ordering validation"
	@${ACTIVATE} isort --profile black --check-only .
	@echo "-> Run black validation"
	@${ACTIVATE} black --check ${BLACK_ARGS} .
	@echo "-> Run docstring validation"
	@${ACTIVATE} pydocstyle fedcode federatedcode

check-deploy:
	@echo "-> Check Django deployment settings"
	${MANAGE} check --deploy

clean:
	@echo "-> Clean the Python env"
	./configure --clean

migrate:
	@echo "-> Apply database migrations"
	${MANAGE} migrate

test:
	@echo "-> Run the test suite"
	@${ACTIVATE} pytest -vvs

docs:
	rm -rf docs/_build/
	@${ACTIVATE} sphinx-build docs/source docs/_build/

postgresdb:
	@echo "-> Configure PostgreSQL database"
	@echo "-> Create database user ${FEDERATEDCODE_DB_NAME}"
	@${SUDO_POSTGRES} createuser --no-createrole --no-superuser --login --inherit --createdb '${FEDERATEDCODE_DB_USER}' || true
	@${SUDO_POSTGRES} psql -c "alter user ${FEDERATEDCODE_DB_USER} with encrypted password '${FEDERATEDCODE_DB_PASSWORD}';" || true
	@echo "-> Drop ${FEDERATEDCODE_DB_NAME} database"
	@${SUDO_POSTGRES} dropdb ${FEDERATEDCODE_DB_NAME} || true
	@echo "-> Create ${FEDERATEDCODE_DB_NAME} database"
	@${SUDO_POSTGRES} createdb --owner=${FEDERATEDCODE_DB_USER} ${POSTGRES_INITDB_ARGS} ${FEDERATEDCODE_DB_NAME}
	@$(MAKE) migrate

backupdb:
	pg_dump -Fc ${FEDERATEDCODE_DB_NAME} > "${FEDERATEDCODE_DB_NAME}-db-${DATE}.dump"

run:
	@echo "-> Starting development server"
	${MANAGE} runserver 8000 --insecure

.PHONY: dev envfile isort black doc8 valid bandit check check-deploy clean migrate test docs  postgresdb backupdb run
