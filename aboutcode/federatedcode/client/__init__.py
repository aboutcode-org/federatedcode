#
# Copyright (c) nexB Inc. and others. All rights reserved.
# FederatedCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/federatedcode for support or download.
# See https://aboutcode.org for more information about AboutCode.org OSS projects.
#

import os
from typing import Union
from urllib.parse import urljoin

import requests
from aboutcode.hashid import get_package_base_dir
from dotenv import load_dotenv
from packageurl import PackageURL

load_dotenv()

FEDERATEDCODE_GITHUB_ACCOUNT_NAME = os.getenv("FEDERATEDCODE_GITHUB_ACCOUNT_NAME")


class ScanNotAvailableError(Exception):
    pass


def get_package_scan(purl: Union[PackageURL, str]):
    """Return the package scan result for a PURL from the FederatedCode Git repository."""

    if not FEDERATEDCODE_GITHUB_ACCOUNT_NAME:
        raise ValueError("Provide ``FEDERATEDCODE_GITHUB_ACCOUNT_NAME`` in .env file.")

    if isinstance(purl, str):
        purl = PackageURL.from_string(purl)

    if not purl.version:
        raise ValueError("Missing version in PURL.")

    package_path = get_package_base_dir(purl=purl)
    package_path_parts = package_path.parts

    repo_name = f"{package_path_parts[0]}/refs/heads/main"
    package_dir_path = "/".join(package_path_parts[1:])
    version = purl.version
    file_name = "scancodeio.json"

    url_parts = [FEDERATEDCODE_GITHUB_ACCOUNT_NAME, repo_name, package_dir_path, version, file_name]

    file_url = urljoin("https://raw.githubusercontent.com", "/".join(url_parts))

    try:
        response = requests.get(file_url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as err:
        if response.status_code == 404:
            raise ScanNotAvailableError(f"No scan available for {purl!s}")
        raise err
