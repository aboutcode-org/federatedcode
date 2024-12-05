#
# Copyright (c) nexB Inc. and others. All rights reserved.
# FederatedCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/federatedcode for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

FROM python:3.10-slim

ENV APP_NAME federatedcode
ENV APP_DIR /opt/$APP_NAME

# Python settings: Force unbuffered stdout and stderr (i.e. they are flushed to terminal immediately)
ENV PYTHONUNBUFFERED 1
# Python settings: do not write pyc files
ENV PYTHONDONTWRITEBYTECODE 1
# Add the app dir in the Python path for entry points availability
ENV PYTHONPATH $PYTHONPATH:$APP_DIR

RUN apt-get update \
 && apt-get install -y --no-install-recommends \
    wait-for-it \
    git \
 && apt-get clean \
 && rm -rf /tmp/* /var/tmp/*

WORKDIR $APP_DIR

RUN mkdir -p /var/$APP_NAME/static/

# Keep the dependencies installation before the COPY of the app/ for proper caching
COPY setup.cfg setup.py requirements.txt pyproject.toml $APP_DIR/
RUN pip install . -c requirements.txt

COPY . $APP_DIR
