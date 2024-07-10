#
# Copyright (c) nexB Inc. and others. All rights reserved.
# VulnerableCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/vulnerablecode for support or download.
# See https://aboutcode.org for more information about nexB OSS projects.
#

import json

from django.core.management.base import BaseCommand
from pydantic.json_schema import GenerateJsonSchema

from fedcode import schemas


class GenerateFederatedCodeJsonSchema(GenerateJsonSchema):
    def generate(self, schema, mode="validation"):
        json_schema = super().generate(schema, mode=mode)
        json_schema["$schema"] = self.schema_dialect
        return json_schema


def get_ordered_schema(schema, schema_path):
    schema["$id"] = f"https://raw.githubusercontent.com/nexB/federatedcode/main/{schema_path}"
    desired_order = [
        "$schema",
        "$id",
        "title",
        "type",
    ]

    ordered_schema = {key: schema[key] for key in desired_order}
    ordered_schema.update({key: schema[key] for key in schema if key not in desired_order})
    return ordered_schema


def gen_schema(model_schema, path):
    schema = model_schema.model_json_schema(schema_generator=GenerateFederatedCodeJsonSchema)
    ordered_schema = get_ordered_schema(schema=schema, schema_path=path)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(ordered_schema, f, indent=2)


class Command(BaseCommand):
    def handle(self, *args, **options):
        gen_schema(
            model_schema=schemas.Vulnerability,
            path="schemas/vulnerability.schema.json",
        )
        gen_schema(
            model_schema=schemas.Package,
            path="schemas/package.schema.json",
        )
