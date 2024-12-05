#
# Copyright (c) nexB Inc. and others. All rights reserved.
# FederatedCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/federatedcode for support or download.
# See https://aboutcode.org for more information about AboutCode.org OSS projects.
#

import saneyaml
from packageurl import PackageURL

from fedcode.activitypub import Activity
from fedcode.activitypub import CreateActivity
from fedcode.activitypub import DeleteActivity
from fedcode.models import Note


def create_note(pkg, note_dict):
    note, _ = Note.objects.get_or_create(acct=pkg.acct, content=saneyaml.dump(note_dict))
    pkg.notes.add(note)
    create_activity = CreateActivity(actor=pkg.to_ap, object=note.to_ap)
    Activity.federate(
        targets=pkg.followers_inboxes,
        body=create_activity.to_ap(),
        key_id=pkg.key_id,
    )


def delete_note(pkg, note_dict):
    note = Note.objects.get(acct=pkg.acct, content=saneyaml.dump(note_dict))
    note_ap = note.to_ap
    note.delete()
    pkg.notes.remove(note)

    deleted_activity = DeleteActivity(actor=pkg.to_ap, object=note_ap)
    Activity.federate(
        targets=pkg.followers_inboxes,
        body=deleted_activity.to_ap,
        key_id=pkg.key_id,
    )


def package_metadata_path_to_purl(path, version=True):
    """
    Return PURL from relative metadata path.

    >>> from pathlib import Path
    >>> path=Path("npm/@angular/animation/3.0.1/scancodeio.json")
    >>> purl=package_metadata_path_to_purl(path)
    >>> assert "pkg:npm/%40angular/animation@3.0.1" == str(purl)
    """
    parts = path.parts
    if len(parts) < 4:
        ValueError("Not a valid package metadata path.")

    purl = f"pkg:{'/'.join(parts[:-2])}"
    if version:
        purl = f"{purl}@{parts[-2]}"
    return PackageURL.from_string(purl=purl)


def get_scan_note(path):
    """Return Note for Package scan."""
    purl = package_metadata_path_to_purl(path=path)

    # TODO: Use tool-alias.yml to get tool for corresponding tool
    # for scan  https://github.com/aboutcode-org/federatedcode/issues/24
    return {
        "purl": str(purl),
        "scans": [
            {
                "tool": "pkg:pypi/scancode-toolkit",
                "file_name": "scancodeio.json",
            },
        ],
    }
