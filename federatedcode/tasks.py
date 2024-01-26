from fedcode.importer import Importer
from fedcode.models import FederateRequest, SyncRequest
from fedcode.signatures import HttpSignature, FEDERATED_CODE_PRIVATE_KEY


def sync_task():
    for sync_r in SyncRequest.objects.all().order_by('created_at'):
        repo = sync_r.repo
        repo.git_repo_obj.remotes.origin.pull()
        importer = Importer(repo, repo.admin)
        importer.run()


def send_federated_requests_task():
    for rq in FederateRequest.objects.all().order_by('created_at'):
        HttpSignature.signed_request(rq.target, rq.body, FEDERATED_CODE_PRIVATE_KEY, rq.key_id)
