#
# Copyright (c) nexB Inc. and others. All rights reserved.
# FederatedCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/federatedcode for support or download.
# See https://aboutcode.org for more information about AboutCode.org OSS projects.
#

from django.core.management.base import BaseCommand
from django.core.management.base import CommandError

from fedcode.pipelines import sync_scancode_scans
from fedcode.pipelines import sync_vulnerablecode

SYNC_REGISTRY = [
    sync_scancode_scans.SyncScanCodeScans,
    sync_vulnerablecode.SyncVulnerableCode,
]

SYNC_REGISTRY = {x.pipeline_id: x for x in SYNC_REGISTRY}


class Command(BaseCommand):
    help = "Sync metadata from git repository"

    def add_arguments(self, parser):
        parser.add_argument(
            "--list",
            action="store_true",
            help="List available pipelines",
        )
        parser.add_argument("--all", action="store_true", help="Sync all repo data.")

        parser.add_argument("pipelines", nargs="*", help="Pipeline ID")

    def handle(self, *args, **options):
        try:
            if options["list"]:
                self.list_pipelines()
            elif options["all"]:
                self.import_data(pipelines=SYNC_REGISTRY.values())
            else:
                pipelines = options["pipelines"]
                if not pipelines:
                    raise CommandError(
                        'Please provide at least one pipeline to execute or use "--all".'
                    )
                self.import_data(validate_pipelines(pipelines))
        except KeyboardInterrupt:
            raise CommandError("Keyboard interrupt received. Stopping...")

    def list_pipelines(self):
        self.stdout.write("Metadata can be synced from the following pipelines:")
        self.stdout.write("\n".join(SYNC_REGISTRY))

    def import_data(self, pipelines):
        """Execute the given ``pipeline``."""
        failed_pipelines = []

        for pipeline in pipelines:
            self.stdout.write(f"Syncing data using {pipeline.pipeline_id}")
            status, error = pipeline().execute()
            if status != 0:
                self.stdout.write(error)
                failed_pipelines.append(pipeline.pipeline_id)

        if failed_pipelines:
            raise CommandError(f"{len(failed_pipelines)} failed!: {','.join(failed_pipelines)}")


def validate_pipelines(pipelines):
    validated_pipelines = []
    unknown_pipelines = []
    for pipeline in pipelines:
        try:
            validated_pipelines.append(SYNC_REGISTRY[pipeline])
        except KeyError:
            unknown_pipelines.append(pipeline)
    if unknown_pipelines:
        raise CommandError(f"Unknown pipelines: {unknown_pipelines}")

    return validated_pipelines
