#
# Copyright (c) nexB Inc. and others. All rights reserved.
# VulnerableCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/vulnerablecode for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#
from django.contrib import admin

from .models import Follow
from .models import Note
from .models import Person
from .models import Package
from .models import RemoteActor
from .models import Repository
from .models import Reputation
from .models import Review
from .models import Service
from .models import Vulnerability
from .models import SyncRequest
from .models import FederateRequest

admin.site.register(Person)
admin.site.register(Service)

admin.site.register(Repository)
admin.site.register(Vulnerability)
admin.site.register(Package)
admin.site.register(Note)
admin.site.register(Follow)
admin.site.register(Review)
admin.site.register(Reputation)

admin.site.register(RemoteActor)
admin.site.register(SyncRequest)
admin.site.register(FederateRequest)
