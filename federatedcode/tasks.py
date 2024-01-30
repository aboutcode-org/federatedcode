#
# Copyright (c) nexB Inc. and others. All rights reserved.
# VulnerableCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/vulnerablecode for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#
from fedcode.importer import Importer
from fedcode.models import FederateRequest, SyncRequest
from fedcode.signatures import HttpSignature, FEDERATED_CODE_PRIVATE_KEY


def sync_task():
    """
    sync_task is a task to run the Importer and save the status
    """
    for sync_r in SyncRequest.objects.all().order_by('created_at'):
        if not sync_r.done:
            try:
                repo = sync_r.repo
                repo.git_repo_obj.remotes.origin.pull()
                importer = Importer(repo, repo.admin)
                importer.run()
                sync_r.done = True
            except Exception as e:
                sync_r.error_message = e
            finally:
                sync_r.save()


def send_fed_req_task():
    """
    send_fed_req_task is a task to send the http signed request to the target and save the status of the request
    """
    for rq in FederateRequest.objects.all().order_by('created_at'):
        if not rq.done:
            try:
                HttpSignature.signed_request(rq.target, rq.body, FEDERATED_CODE_PRIVATE_KEY, rq.key_id)
                rq.done = True
                rq.save()
            except Exception as e:
                rq.error_message = e
            finally:
                rq.save()
