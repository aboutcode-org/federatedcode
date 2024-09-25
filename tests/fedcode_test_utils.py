#
# Copyright (c) nexB Inc. and others. All rights reserved.
# FederatedCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/federatedcode for support or download.
# See https://aboutcode.org for more information about AboutCode.org OSS projects.
#

import pytest
from django.db.models.signals import post_save


@pytest.fixture(autouse=True)
def mute_post_save_signal(request):
    """
    copied from https://www.cameronmaske.com/muting-django-signals-with-a-pytest-fixture/
    """
    post_save.receivers = []
