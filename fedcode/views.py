#
# Copyright (c) nexB Inc. and others. All rights reserved.
# FederatedCode is a trademark of nexB Inc.
# SPDX-License-Identifier: Apache-2.0
# See http://www.apache.org/licenses/LICENSE-2.0 for the license text.
# See https://github.com/nexB/federatedcode for support or download.
# See https://aboutcode.org for more information about AboutCode.org OSS projects.
#
import difflib
import json
import logging
import os.path

import requests
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.contrib.auth.models import auth
from django.contrib.auth.views import LoginView
from django.contrib.contenttypes.models import ContentType
from django.core.paginator import Paginator
from django.http import Http404
from django.http import HttpResponse
from django.http import HttpResponseBadRequest
from django.http import HttpResponseForbidden
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.views.generic import CreateView
from django.views.generic import DetailView
from django.views.generic import FormView
from django.views.generic import ListView
from django.views.generic import TemplateView
from django.views.generic.edit import FormMixin
from django.views.generic.edit import UpdateView

from fedcode.activitypub import AP_CONTEXT
from fedcode.activitypub import create_activity_obj
from fedcode.activitypub import has_valid_header
from fedcode.forms import CreateGitRepoForm
from fedcode.forms import CreateNoteForm
from fedcode.forms import CreateReviewForm
from fedcode.forms import FetchForm
from fedcode.forms import PersonSignUpForm
from fedcode.forms import ReviewStatusForm
from fedcode.forms import SearchPackageForm
from fedcode.forms import SearchRepositoryForm
from fedcode.forms import SearchReviewForm
from fedcode.forms import SubscribePackageForm
from fedcode.models import Follow
from fedcode.models import Note
from fedcode.models import Package
from fedcode.models import Person
from fedcode.models import Repository
from fedcode.models import Reputation
from fedcode.models import Review
from fedcode.models import SyncRequest
from fedcode.models import Vulnerability
from fedcode.signatures import FEDERATEDCODE_PUBLIC_KEY
from fedcode.signatures import HttpSignature
from fedcode.utils import ap_collection
from fedcode.utils import full_reverse
from fedcode.utils import generate_webfinger
from fedcode.utils import load_git_file
from fedcode.utils import parse_webfinger
from fedcode.utils import webfinger_actor
from federatedcode.settings import AP_CONTENT_TYPE
from federatedcode.settings import FEDERATEDCODE_CLIENT_ID
from federatedcode.settings import FEDERATEDCODE_CLIENT_SECRET
from federatedcode.settings import FEDERATEDCODE_DOMAIN

logger = logging.getLogger(__name__)


def logout(request):
    auth.logout(request)
    return redirect("login")


class WebfingerView(View):
    def get(self, request):
        """/.well-known/webfinger?resource=acct:gargron@mastodon.social"""
        resource = request.GET.get("resource")

        if not resource:
            return HttpResponseBadRequest("No resource found")

        obj, domain = parse_webfinger(resource)

        if FEDERATEDCODE_DOMAIN != domain or not obj:
            return HttpResponseBadRequest("Invalid domain")

        if obj.startswith("pkg:"):
            try:
                package = Package.objects.get(purl=obj)
            except Package.DoesNotExist:
                return HttpResponseBadRequest("Not an Purl resource")

            return render(
                request,
                "webfinger_package.json",
                status=200,
                content_type="application/jrd+json",
                context={
                    "resource": resource,
                    "domain": FEDERATEDCODE_DOMAIN,
                    "purl_string": package.purl,
                },
            )
        else:
            try:
                user = User.objects.get(username=obj)
            except User.DoesNotExist:
                return HttpResponseBadRequest("Not an account resource")

            return render(
                request,
                "webfinger_user.json",
                status=200,
                content_type="application/jrd+json",
                context={
                    "resource": resource,
                    "domain": FEDERATEDCODE_DOMAIN,
                    "username": user.username,
                },
            )


class HomeView(View):
    def get(self, request, *args, **kwargs):
        if hasattr(self.request.user, "person"):
            packages = [
                generate_webfinger(follow.package.purl)
                for follow in Follow.objects.filter(person=self.request.user.person)
            ]
            note_list = Note.objects.filter(acct__in=packages).order_by("updated_at__minute")
            paginator = Paginator(note_list, 10)
            page_number = request.GET.get("page")
            page_note = paginator.get_page(page_number)
            return render(request, "home.html", context={"page_note": page_note})
        elif hasattr(self.request.user, "service"):
            return redirect("repo-list")
        else:
            return redirect("login")


class PersonView(DetailView):
    model = Person
    template_name = "user_profile.html"
    slug_field = "user__username"
    context_object_name = "person"

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(**kwargs)
        following_list = Follow.objects.filter(person=self.object)
        paginator = Paginator(following_list, 10)
        page_number = self.request.GET.get("page")
        context["followings"] = paginator.get_page(page_number)
        context["follow_count"] = following_list.count()
        return context


class PackageView(DetailView, FormMixin):
    model = Package
    template_name = "pkg_profile.html"
    slug_field = "purl"
    context_object_name = "package"
    form_class = CreateNoteForm

    def get_success_url(self):
        return self.request.path

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # slug = purl_string

        context["purl_notes"] = Note.objects.filter(acct=generate_webfinger(self.kwargs["slug"]))

        context["followers"] = Follow.objects.filter(package=self.object)

        if self.request.user.is_authenticated:
            context["is_user_follow"] = (
                True
                if Follow.objects.filter(
                    package=self.object, person__user=self.request.user
                ).first()
                else False
            )

        context["note_form"] = CreateNoteForm()
        context["subscribe_form"] = SubscribePackageForm()
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        note_form = self.get_form()
        if note_form.is_valid():
            note_form.instance.acct = generate_webfinger(self.kwargs["slug"])
            note_form.instance.note_type = 0
            note_form.save()
            return super(PackageView, self).form_valid(note_form)
        else:
            return self.form_invalid(note_form)


def is_service_user(view):
    def wrapper(request, *args, **kwargs):
        if hasattr(request.user, "service"):
            return view(request, *args, **kwargs)
        else:
            return HttpResponseForbidden()

    return wrapper


@method_decorator(is_service_user, name="dispatch")
class CreatGitView(LoginRequiredMixin, CreateView):
    model = Repository
    form_class = CreateGitRepoForm
    template_name = "create_repository.html"
    success_url = reverse_lazy("repo-list")

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.admin = self.request.user.service
        try:
            self.object.save()
            messages.success(self.request, "Git repo successfully created")
        except Exception as e:  #
            logger.error(f"Error occurred while creating git repo {e}")
            messages.error(self.request, "An error occurred")

        return super(CreatGitView, self).form_valid(form)


@method_decorator(is_service_user, name="dispatch")
class CreateSync(LoginRequiredMixin, View):
    def post(self, request, repository_id):
        try:
            repo = Repository.objects.get(id=repository_id)
            if repo.admin == self.request.user.service:
                SyncRequest.objects.create(repo=repo)
                messages.success(self.request, "The sync request was sent successfully")
            else:
                return HttpResponseForbidden("Invalid Git Repository Admin")
        except Repository.DoesNotExist:
            return HttpResponseBadRequest("Invalid Git Repository")
        return redirect("repo-list")


class UserLogin(LoginView):
    template_name = "login.html"
    next_page = "/review-list"


class PersonSignUp(FormView):
    form_class = PersonSignUpForm
    success_url = "/review-list"
    template_name = "user_sign_up.html"

    def form_valid(self, form):
        user = form.save()
        if user:
            person = Person.objects.create(user=user)
            person.save()
            login(self.request, user, backend="django.contrib.auth.backends.ModelBackend")
        return super(PersonSignUp, self).form_valid(form)


class RepositoryListView(ListView, FormMixin):
    model = Repository
    context_object_name = "repo_list"
    template_name = "repo_list.html"
    paginate_by = 10
    form_class = SearchRepositoryForm

    def get_queryset(self):
        form = self.form_class(self.request.GET)
        if form.is_valid():
            return Repository.objects.filter(url__icontains=form.cleaned_data.get("search"))
        return Repository.objects.all()


class ReviewListView(ListView, FormMixin):
    model = Review
    context_object_name = "review_list"
    template_name = "review_list.html"
    paginate_by = 10
    form_class = SearchReviewForm

    def get_queryset(self):
        form = self.form_class(self.request.GET)
        if form.is_valid():
            return Review.objects.filter(headline__icontains=form.cleaned_data.get("search"))
        return Review.objects.all()


class PackageListView(ListView, FormMixin):
    model = Package
    context_object_name = "package_list"
    template_name = "pkg_list.html"
    paginate_by = 20
    form_class = SearchPackageForm

    def get_queryset(self):
        form = self.form_class(self.request.GET)
        if form.is_valid():
            return Package.objects.filter(purl__icontains=form.cleaned_data.get("search"))
        return Package.objects.all()


class ReviewView(LoginRequiredMixin, TemplateView):
    template_name = "review.html"

    def get_context_data(self, request, **kwargs):
        context = super().get_context_data(**kwargs)
        context["review"] = get_object_or_404(Review, id=self.kwargs["review_id"])
        vul_source = context["review"].data.splitlines()
        vul_target = load_git_file(
            git_repo_obj=context["review"].repository.git_repo_obj,
            filename=context["review"].filepath,
            commit_id=context["review"].commit,
        ).splitlines()
        d = difflib.HtmlDiff()
        context["patch"] = d.make_table(
            vul_source, vul_target, fromdesc="original", todesc="modified"
        )
        return context

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(request, **kwargs)
        return render(
            request,
            self.template_name,
            {
                "status_form": ReviewStatusForm(),
                "comment_form": CreateNoteForm(),
                **context,
            },
        )

    def post(self, request, *args, **kwargs):
        context = self.get_context_data(request, **kwargs)
        status_form = ReviewStatusForm(request.POST, instance=context["review"])
        comment_form = CreateNoteForm(request.POST)
        if status_form.is_bound and status_form.is_valid():
            status_form.save()

        elif comment_form.is_bound and comment_form.is_valid():
            comment_form.save(commit=False)
            comment_form.instance.acct = generate_webfinger(request.user.username)
            comment = comment_form.save()
            context["review"].notes.add(comment)
            context["review"].save()

        status_form = ReviewStatusForm()
        comment_form = CreateNoteForm()
        context = self.get_context_data(request, **kwargs)
        return render(
            request,
            self.template_name,
            {"status_form": status_form, "comment_form": comment_form, **context},
        )


def fetch_repository_file(request, repository_id):
    if request.headers.get("x-requested-with") == "XMLHttpRequest" and request.method == "POST":
        request_body = json.load(request)
        path = request_body.get("path")

        repo = get_object_or_404(Repository, id=repository_id).git_repo_obj
        for entry in repo.commit().tree.traverse():
            if path == entry.path:
                with open(entry.abspath) as f:
                    return JsonResponse({"filename": path, "text": f.read()})
    return HttpResponseBadRequest("Can't fetch this file")


@login_required
def obj_vote(request, obj_id, obj_type):
    if request.headers.get("x-requested-with") == "XMLHttpRequest" and request.method == "PUT":
        user_webfinger = generate_webfinger(request.user.username)
        if obj_type == "review":
            obj = get_object_or_404(Review, id=obj_id)
        elif obj_type == "note":
            obj = get_object_or_404(Note, id=obj_id)
        else:
            return HttpResponseBadRequest("Invalid object type to vote")

        request_body = json.load(request)
        try:
            content_type = ContentType.objects.get_for_model(
                Review if obj_type == "review" else Note
            ).id
            rep_obj = Reputation.objects.get(
                voter=user_webfinger,
                object_id=obj.id,
                content_type=content_type,
            )
            if rep_obj:
                vote_type = "vote-down" if rep_obj.positive else "vote-up"
                rep_obj.delete()
                return JsonResponse(
                    {
                        "message": "The vote has been removed successfully",
                        "vote-type": vote_type,
                    }
                )
        except Reputation.DoesNotExist:
            vote_type = request_body.get("vote-type")
            rep_obj = None
            if vote_type == "vote-up":
                rep_obj = Reputation.objects.create(
                    voter=user_webfinger,
                    content_object=obj,
                    positive=True,
                )
            elif vote_type == "vote-down":
                rep_obj = (
                    Reputation.objects.create(
                        voter=user_webfinger,
                        content_object=obj,
                        positive=False,
                    ),
                )

            else:
                return HttpResponseBadRequest("Invalid vote-type request")

            if rep_obj:
                return JsonResponse(
                    {
                        "message": "Voting completed successfully",
                        "vote-type": vote_type,
                    }
                )
    return HttpResponseBadRequest("Invalid vote request")


class FollowPackageView(View):
    def post(self, request, *args, **kwargs):
        package = Package.objects.get(purl=self.kwargs["purl_string"])
        if request.user.is_authenticated:
            if "follow" in request.POST:
                follow_obj, _ = Follow.objects.get_or_create(
                    person=self.request.user.person, package=package
                )

            elif "unfollow" in request.POST:
                try:
                    follow_obj = Follow.objects.get(
                        person=self.request.user.person, package=package
                    )
                    follow_obj.delete()
                except Follow.DoesNotExist:
                    return HttpResponseBadRequest(
                        "Some thing went wrong when you try to unfollow this purl"
                    )
        elif request.user.is_anonymous:
            form = SubscribePackageForm(request.POST)
            if form.is_valid():
                user, domain = parse_webfinger(form.cleaned_data.get("acct"))
                remote_actor_url = webfinger_actor(domain, user)

                payload = json.dumps(
                    {
                        **AP_CONTEXT,
                        "type": "Follow",
                        "actor": {
                            "type": "Person",
                            "id": remote_actor_url,
                        },
                        "object": {
                            "type": "Purl",
                            "id": package.absolute_url_ap,
                        },
                        "to": [remote_actor_url],
                    }
                )

                activity = create_activity_obj(payload)
                _activity_response = activity.handler()
                return JsonResponse(
                    {
                        "redirect_url": f"https://{domain}/authorize_interaction?uri={remote_actor_url}"
                    }
                )
            else:
                return HttpResponseBadRequest()

        return redirect(".")


class CreateReview(LoginRequiredMixin, TemplateView):
    template_name = "create_review.html"

    def get_context_data(self, request, **kwargs):
        context = super().get_context_data(**kwargs)
        repo = Repository.objects.get(id=self.kwargs["repository_id"])
        context["git_files_tree"] = [
            entry.path
            for entry in repo.git_repo_obj.commit().tree.traverse()
            if entry.type == "blob"
        ]
        return context

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(request, **kwargs)
        return render(
            request,
            self.template_name,
            {
                **context,
                "create_review_form": CreateReviewForm(),
                "fetch_form": FetchForm(),
            },
        )

    def post(self, request, *args, **kwargs):
        create_review_form = CreateReviewForm(request.POST)
        if create_review_form.is_valid() and request.user.person:
            repo = Repository.objects.get(id=self.kwargs["repository_id"])
            commit = repo.git_repo_obj.head.commit
            review = Review.objects.create(
                headline=create_review_form.cleaned_data["headline"],
                data=create_review_form.cleaned_data["data"],
                author=request.user.person,
                repository=repo,
                filepath=create_review_form.cleaned_data["filename"],
                commit=commit,
            )
            review.save()
        context = self.get_context_data(request, **kwargs)
        messages.add_message(request, messages.SUCCESS, "The review was created successfully.")
        return render(
            request,
            self.template_name,
            {
                **context,
                "create_review_form": CreateReviewForm(),
                "fetch_form": FetchForm(),
            },
        )


class NoteView(LoginRequiredMixin, FormMixin, DetailView):
    template_name = "note.html"
    model = Note
    context_object_name = "note"
    slug_field = "id"
    slug_url_kwarg = "uuid"
    form_class = CreateNoteForm

    def get_context_data(self, **kwargs):
        context = super(NoteView, self).get_context_data(**kwargs)
        context["form"] = CreateNoteForm()
        return context

    def post(self, request, *args, **kwargs):
        """Create a note"""
        comment_form = self.get_form()
        if comment_form.is_valid():
            comment_form.instance.acct = generate_webfinger(request.user.username)
            comment_form.instance.reply_to = Note.objects.get(id=self.kwargs["uuid"])
            comment_form.save()
            return self.get(request)
        else:
            return self.form_invalid(comment_form)


@method_decorator(has_valid_header, name="dispatch")
class UserProfile(View):
    def get(self, request, *args, **kwargs):
        """"""
        try:
            user = User.objects.get(username=kwargs["username"])
        except User.DoesNotExist:
            return HttpResponseBadRequest("User doesn't exist")

        if request.GET.get("main-key"):
            return HttpResponse(
                user.person.public_key if hasattr(user, "person") else user.service.public_key
            )

        if hasattr(user, "person"):
            return JsonResponse(user.person.to_ap, content_type=AP_CONTENT_TYPE)
        elif hasattr(user, "service"):
            return JsonResponse(user.service.to_ap, content_type=AP_CONTENT_TYPE)
        else:
            return HttpResponseBadRequest("Invalid type user")


class PersonUpdateView(UpdateView):
    model = Person
    fields = ["avatar", "summary"]
    template_name = "update_profile.html"
    slug_field = "user__username"

    def get_success_url(self):
        return reverse_lazy("user-profile", kwargs={"slug": self.object.user.username})

    def get_form(self, *args, **kwargs):
        form = super(PersonUpdateView, self).get_form(*args, **kwargs)
        form.fields["summary"].widget.attrs["class"] = "textarea"
        form.fields["summary"].help_text = ""
        form.fields["avatar"].label = ""
        return form


@method_decorator(has_valid_header, name="dispatch")
class PackageProfile(View):
    def get(self, request, *args, **kwargs):
        """"""
        try:
            package = Package.objects.get(purl=kwargs["purl_string"])
        except Package.DoesNotExist:
            return HttpResponseBadRequest("Invalid type user")

        if request.GET.get("main-key"):
            return HttpResponse(package.public_key)

        return JsonResponse(package.to_ap, content_type=AP_CONTENT_TYPE)


@method_decorator(has_valid_header, name="dispatch")
class UserInbox(View):
    def get(self, request, *args, **kwargs):
        """You can GET from your inbox to read your latest messages
        (client-to-server; this is like reading your social network stream)"""
        if hasattr(request.user, "person") and request.user.username == kwargs["username"]:
            purl_followers = [
                generate_webfinger(follow.package.purl)
                for follow in Follow.objects.filter(person=request.user.person)
            ]
            note_list = Note.objects.filter(acct__in=purl_followers).order_by("updated_at__minute")
            reviews = Review.objects.filter(author=request.user.person)
            return JsonResponse(
                {"notes": ap_collection(note_list), "reviews": ap_collection(reviews)},
                content_type=AP_CONTENT_TYPE,
            )

    def post(self, request, *args, **kwargs):
        """You can POST to someone's inbox to send them a message
        (server-to-server / federation only... this is federation!)"""
        return NotImplementedError


@method_decorator(has_valid_header, name="dispatch")
class UserOutbox(View):
    def get(self, request, *args, **kwargs):
        """You can GET from someone's outbox to see what messages they've posted
        (or at least the ones you're authorized to see).
        (client-to-server and/or server-to-server)"""
        try:
            user = User.objects.get(username=kwargs["username"])
        except User.DoesNotExist:
            user = None

        if hasattr(user, "person"):
            notes = Note.objects.filter(acct=user.person.acct)
            reviews = Review.objects.filter(author=user.person)
            return JsonResponse(
                {
                    "notes": ap_collection(notes),
                    "reviews": ap_collection(reviews),
                },
                content_type=AP_CONTENT_TYPE,
            )
        elif hasattr(user, "service"):
            repos = Repository.objects.filter(admin=user.service)
            return JsonResponse(
                {
                    "repositories": ap_collection(repos),
                },
                content_type=AP_CONTENT_TYPE,
            )
        else:
            return HttpResponseBadRequest("Can't find this user")

    @csrf_exempt
    def post(self, request, *args, **kwargs):
        """You can POST to your outbox to send messages to the world (client-to-server)"""
        if request.user.is_authenticated and request.user.username == kwargs["username"]:
            activity = create_activity_obj(request.body)
            if activity:
                return activity.handler()

        return HttpResponseBadRequest("Invalid message")


@method_decorator(has_valid_header, name="dispatch")
class PackageInbox(View):
    def get(self, request, *args, **kwargs):
        """
        You can GET from your inbox to read your latest messages
        (client-to-server; this is like reading your social network stream)
        """
        try:
            package = Package.objects.get(purl=kwargs["purl_string"])
        except Package.DoesNotExist:
            package = None

        if hasattr(request.user, "service") and package:
            return JsonResponse(
                {
                    "notes": ap_collection(package.notes.all()),
                },
                content_type="application/activity+json",
            )
        return HttpResponseBadRequest()

    @csrf_exempt
    def post(self, request, *args, **kwargs):
        """
        You can POST to someone's inbox to send them a message
        (server-to-server / federation only... this is federation!)
        """
        HttpSignature.verify_request(request, FEDERATEDCODE_PUBLIC_KEY)
        activity = create_activity_obj(request.body)
        activity_response = activity.handler()
        return activity_response


@method_decorator(has_valid_header, name="dispatch")
class PackageOutbox(View):
    def get(self, request, *args, **kwargs):
        """GET from someone's outbox to see what messages they've posted
        (or at least the ones you're authorized to see).
        (client-to-server and/or server-to-server)"""

        actor = Package.objects.get(purl=kwargs["purl_string"])
        return JsonResponse(
            {"notes": ap_collection(actor.notes)},
            content_type=AP_CONTENT_TYPE,
        )

    def post(self, request, *args, **kwargs):
        """You can POST to your outbox to send messages to the world (client-to-server)"""
        try:
            actor = Package.objects.get(purl=kwargs["purl_string"])
        except Package.DoesNotExist:
            return HttpResponseBadRequest("Invalid purl")

        if (
            request.user.is_authenticated
            and hasattr(request.user, "service")
            and actor.service == request.user.service
        ):
            activity = create_activity_obj(request.body)
            return activity.handler()
        return HttpResponseBadRequest("Invalid Message")


def redirect_repository(request, repository_id):
    try:
        repo = Repository.objects.get(id=repository_id)
    except Repository.DoesNotExist:
        raise Http404("Repository does not exist")
    return redirect(repo.url)


def redirect_vulnerability(request, vulnerability_id):
    try:
        vul = Vulnerability.objects.get(id=vulnerability_id)
        vul_filepath = os.path.join(
            vul.repo.path,
            f"./aboutcode-vulnerabilities-{vulnerability_id[5:7]}/{vulnerability_id[10:12]}"
            f"/{vulnerability_id}/{vulnerability_id}.yml",
        )
        with open(vul_filepath) as f:
            return HttpResponse(json.dumps(f.read()))

    except Vulnerability.DoesNotExist:
        return Http404("Vulnerability does not exist")


class UserFollowing(View):
    def get(self, request, *args, **kwargs):
        followings = Follow.objects.filter(person__user__username=self.kwargs["username"])
        return JsonResponse(
            [full_reverse(following) for following in followings],
            content_type=AP_CONTENT_TYPE,
        )


class PackageFollowers(View):
    def get(self, request, *args, **kwargs):
        followers = Follow.objects.filter(purl__string=self.kwargs["purl_string"])
        return JsonResponse(
            [full_reverse(following) for following in followers],
            content_type=AP_CONTENT_TYPE,
        )


@require_http_methods(["POST"])
@csrf_exempt
def token(request):
    payload = json.loads(request.body)
    r = requests.post(
        "http://127.0.0.1:8000/o/token/",
        headers={"content-type": "application/x-www-form-urlencoded"},
        data={
            "grant_type": "password",
            "username": payload["username"],
            "password": payload["password"],
            "client_id": FEDERATEDCODE_CLIENT_ID,
            "client_secret": FEDERATEDCODE_CLIENT_SECRET,
        },
    )
    return JsonResponse(json.loads(r.content), status=r.status_code, content_type=AP_CONTENT_TYPE)


@require_http_methods(["POST"])
@csrf_exempt
def refresh_token(request):
    payload = json.loads(request.body)
    r = requests.post(
        "http://127.0.0.1:8000/o/token/",
        headers={"content-type": "application/x-www-form-urlencoded"},
        data={
            "grant_type": "refresh_token",
            "refresh_token": payload["refresh_token"],
            "client_id": FEDERATEDCODE_CLIENT_ID,
            "client_secret": FEDERATEDCODE_CLIENT_SECRET,
        },
    )
    return JsonResponse(json.loads(r.text), status=r.status_code, content_type=AP_CONTENT_TYPE)


@require_http_methods(["POST"])
@csrf_exempt
def revoke_token(request):
    payload = json.loads(request.body)
    r = requests.post(
        "http://127.0.0.1:8000/o/revoke_token/",
        headers={"content-type": "application/x-www-form-urlencoded"},
        data={
            "token": payload["token"],
            "client_id": FEDERATEDCODE_CLIENT_ID,
            "client_secret": FEDERATEDCODE_CLIENT_SECRET,
        },
    )
    return JsonResponse(json.loads(r.content), status=r.status_code, content_type=AP_CONTENT_TYPE)
