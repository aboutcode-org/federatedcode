#
# Copyright (c) nexB Inc. and others. All rights reserved.
# FederatedCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/federatedcode for support or download.
# See https://aboutcode.org for more information about AboutCode.org OSS projects.
#
from django import template
from packageurl import PackageURL

from federatedcode.settings import STATIC_URL

register = template.Library()


@register.filter
def get_pkg_image(purl_webfinger):
    """
    Return the path of the image package
    """
    try:
        purl, _ = purl_webfinger.split("@")
        package_type = PackageURL.from_string(purl).type
        return STATIC_URL + "pictogram-gh-pages/" + package_type + "/" + package_type + ".png"
    except ValueError:
        return ""
