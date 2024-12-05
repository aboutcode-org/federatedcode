#
# Copyright (c) nexB Inc. and others. All rights reserved.
# FederatedCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/federatedcode for support or download.
# See https://aboutcode.org for more information about AboutCode.org OSS projects.
#
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include
from django.urls import path

from fedcode import views
from fedcode.views import CreateReview
from fedcode.views import CreateSync
from fedcode.views import CreatGitView
from fedcode.views import FollowPackageView
from fedcode.views import HomeView
from fedcode.views import NoteView
from fedcode.views import PackageFollowers
from fedcode.views import PackageInbox
from fedcode.views import PackageListView
from fedcode.views import PackageOutbox
from fedcode.views import PackageProfile
from fedcode.views import PackageView
from fedcode.views import PersonSignUp
from fedcode.views import PersonUpdateView
from fedcode.views import PersonView
from fedcode.views import RepositoryListView
from fedcode.views import ReviewListView
from fedcode.views import ReviewView
from fedcode.views import UserFollowing
from fedcode.views import UserInbox
from fedcode.views import UserLogin
from fedcode.views import UserOutbox
from fedcode.views import UserProfile
from fedcode.views import WebfingerView
from fedcode.views import fetch_repository_file
from fedcode.views import logout
from fedcode.views import obj_vote
from fedcode.views import redirect_repository
from fedcode.views import redirect_vulnerability

urlpatterns = [
    path("admin/", admin.site.urls),
    path(".well-known/webfinger", WebfingerView.as_view(), name="web-finger"),
    path("", HomeView.as_view(), name="home-page"),
    path("users/@<str:slug>", PersonView.as_view(), name="user-profile"),
    path("users/@<str:slug>/edit", PersonUpdateView.as_view(), name="user-edit"),
    path("purls/@<path:slug>/", PackageView.as_view(), name="purl-profile"),
    path("purls/@<path:purl_string>/follow", FollowPackageView.as_view(), name="purl-follow"),
    path("accounts/sign-up", PersonSignUp.as_view(), name="signup"),
    path("accounts/login/", UserLogin.as_view(), name="login"),
    path("accounts/logout", logout, name="logout"),
    path("create-repo", CreatGitView.as_view(), name="repo-create"),
    path("repo-list", RepositoryListView.as_view(), name="repo-list"),
    path("purl-list", PackageListView.as_view(), name="purl-list"),
    path(
        "repository/<uuid:repository_id>/create-review/",
        CreateReview.as_view(),
        name="review-create",
    ),
    path(
        "repository/<uuid:repository_id>/sync-repo/",
        CreateSync.as_view(),
        name="sync-activity",
    ),
    path("review-list", ReviewListView.as_view(), name="review-list"),
    path("reviews/<uuid:review_id>/", ReviewView.as_view(), name="review-page"),
    path("reviews/<uuid:obj_id>/votes/", obj_vote, {"obj_type": "review"}, name="review-votes"),
    path("notes/<uuid:obj_id>/votes/", obj_vote, {"obj_type": "note"}, name="comment-votes"),
    path("repository/<uuid:repository_id>/", redirect_repository, name="repository-page"),
    path(
        "repository/<uuid:repository_id>/fetch",
        fetch_repository_file,
        name="repository-fetch",
    ),
    path(
        "vulnerability/<str:vulnerability_id>/",
        redirect_vulnerability,
        name="vulnerability-page",
    ),
    path("notes/<uuid:uuid>", NoteView.as_view(), name="note-page"),
    path("api/v0/users/@<str:username>", UserProfile.as_view(), name="user-ap-profile"),
    path(
        "api/v0/purls/@<path:purl_string>/",
        PackageProfile.as_view(),
        name="purl-ap-profile",
    ),
    path("api/v0/users/@<str:username>/inbox", UserInbox.as_view(), name="user-inbox"),
    path("api/v0/users/@<str:username>/outbox", UserOutbox.as_view(), name="user-outbox"),
    path("api/v0/purls/@<path:purl_string>/inbox", PackageInbox.as_view(), name="purl-inbox"),
    path(
        "api/v0/purls/@<path:purl_string>/outbox",
        PackageOutbox.as_view(),
        name="purl-outbox",
    ),
    path(
        "api/v0/users/@<str:username>/following/",
        UserFollowing.as_view(),
        name="user-following",
    ),
    path(
        "api/v0/purls/@<path:purl_string>/followers/",
        PackageFollowers.as_view(),
        name="purl-followers",
    ),
    path("auth/token/", views.token),
    path("auth/refresh_token/", views.refresh_token),
    path("auth/revoke_token/", views.revoke_token),
    path("o/", include("oauth2_provider.urls", namespace="oauth2_provider")),
]

if settings.DEBUG and settings.DEBUG_TOOLBAR:
    urlpatterns.append(path("__debug__/", include("debug_toolbar.urls")))
