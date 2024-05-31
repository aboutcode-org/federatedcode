#
# Copyright (c) nexB Inc. and others. All rights reserved.
# FederatedCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/federatedcode for support or download.
# See https://aboutcode.org for more information about AboutCode.org OSS projects.
#
from django.contrib import admin

from .models import FederateRequest
from .models import Follow
from .models import Note
from .models import Package
from .models import Person
from .models import RemoteActor
from .models import Repository
from .models import Reputation
from .models import Review
from .models import Service
from .models import SyncRequest
from .models import Vulnerability

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
