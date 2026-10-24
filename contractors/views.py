import os

from django.contrib.admin.views.decorators import staff_member_required
from django.http import FileResponse

from .forms import VerificationDocumentForm
from .models import VerificationDocument


from decimal import Decimal, InvalidOperation
from functools import wraps

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Avg, Count, F, Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import (
    ContractorProfileForm,
    ProjectForm,
    ProjectImageFormSet,
    QuoteRequestForm,
    QuoteResponseForm,
    ReviewForm,
    SignUpForm,
)
from .models import ContractorProfile, Project, QuoteRequest, Review, Specialty


# ---------------------------------------------------------------- access control
def role_required(role, denied_message):
    """Build a decorator that allows only logged-in users with the given role."""

    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            account = getattr(request.user, "account", None)
            if account is None or account.role != role:
                messages.error(request, denied_message)
                return redirect("contractors:home")
            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


contractor_required = role_required("contractor", "That page is only for contractor accounts.")
client_required = role_required("client", "That page is only for client accounts.")


def with_ratings(queryset):
    """Add avg_rating and review_count to every contractor in the queryset."""
    return queryset.annotate(
        avg_rating=Avg("reviews__rating"),
        review_count=Count("reviews", distinct=True),
    )


# ---------------------------------------------------------------- public pages
def home(request):
    verified = ContractorProfile.objects.filter(verified=True)
    featured = with_ratings(verified).prefetch_related("specialties")[:6]
    context = {
        "featured": featured,
        "verified_count": verified.count(),
        "city_count": verified.values("city").distinct().count(),
        "specialty_count": Specialty.objects.count(),
    }
    return render(request, "contractors/home.html", context)


def contractor_list(request):
    contractors = with_ratings(
        ContractorProfile.objects.filter(verified=True)
    ).prefetch_related("specialties")

    # Read the search options from the URL (?q=...&specialty=...)
    q = request.GET.get("q", "").strip()
    specialty = request.GET.get("specialty", "")
    budget = request.GET.get("budget", "").strip()
    experience = request.GET.get("experience", "").strip()
    sort = request.GET.get("sort", "")

    if q:
        contractors = contractors.filter(
            Q(company_name__icontains=q) | Q(city__icontains=q) | Q(about__icontains=q)
        )

    if specialty.isdigit():
        contractors = contractors.filter(specialties__id=specialty)

    if budget:
        try:
            amount = Decimal(budget)
            # keep contractors whose budget range includes the client's budget
            contractors = contractors.filter(min_budget__lte=amount, max_budget__gte=amount)
        except InvalidOperation:
            pass  # ignore a badly typed number instead of crashing

    if experience.isdigit():
        contractors = contractors.filter(experience_years__gte=int(experience))

    if sort == "experience":
        contractors = contractors.order_by("-experience_years")
    elif sort == "budget_low":
        contractors = contractors.order_by("min_budget")
    elif sort == "rating":
        # nulls_last keeps unrated contractors at the bottom on every database
        contractors = contractors.order_by(F("avg_rating").desc(nulls_last=True), "-review_count")

    paginator = Paginator(contractors, 9)
    page_obj = paginator.get_page(request.GET.get("page"))

    # Keep the filters in the page links (everything except "page")
    params = request.GET.copy()
    params.pop("page", None)

    context = {
        "page_obj": page_obj,
        "total": paginator.count,
        "specialties": Specialty.objects.all(),
        "q": q,
        "specialty": specialty,
        "budget": budget,
        "experience": experience,
        "sort": sort,
        "querystring": params.urlencode(),
    }
    return render(request, "contractors/list.html", context)


def contractor_detail(request, pk):
    # Only verified contractors have public pages; anything else is a 404
    queryset = with_ratings(
        ContractorProfile.objects.filter(verified=True)
    ).prefetch_related("specialties")
    contractor = get_object_or_404(queryset, pk=pk)
    projects = contractor.projects.select_related("specialty").prefetch_related("images")
    reviews = contractor.reviews.select_related("client")

    # Can this visitor write a review? Only a client whose request was accepted.
    can_review = False
    my_review = None
    account = getattr(request.user, "account", None)
    if account is not None and account.role == "client":
        can_review = QuoteRequest.objects.filter(
            client=request.user, contractor=contractor, status="accepted"
        ).exists()
        my_review = reviews.filter(client=request.user).first()

    return render(
        request,
        "contractors/detail.html",
        {
            "contractor": contractor,
            "projects": projects,
            "reviews": reviews,
            "can_review": can_review,
            "my_review": my_review,
        },
    )


# ---------------------------------------------------------------- accounts
def signup(request):
    if request.user.is_authenticated:
        return redirect("contractors:home")

    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Welcome to Nirmaan, {user.first_name}!")
            if user.account.role == "contractor":
                return redirect("contractors:dashboard")
            return redirect("contractors:home")
    else:
        role = request.GET.get("role")
        initial = {"role": role} if role in ("client", "contractor") else {}
        form = SignUpForm(initial=initial)

    return render(request, "contractors/signup.html", {"form": form})


# ---------------------------------------------------------------- contractor dashboard
@contractor_required
def dashboard(request):
    profile = ContractorProfile.objects.filter(user=request.user).first()
    projects = []
    pending_requests = 0
    if profile:
        projects = profile.projects.select_related("specialty").prefetch_related("images")
        pending_requests = profile.quote_requests.filter(status="pending").count()
    return render(
        request,
        "contractors/dashboard.html",
        {"profile": profile, "projects": projects, "pending_requests": pending_requests},
    )


@contractor_required
def profile_edit(request):
    profile = ContractorProfile.objects.filter(user=request.user).first()

    if request.method == "POST":
        form = ContractorProfileForm(request.POST, instance=profile)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.user = request.user  # the owner is always the logged-in user
            obj.save()
            form.save_m2m()  # saves the many-to-many "specialties"
            messages.success(request, "Your company profile has been saved.")
            return redirect("contractors:dashboard")
    else:
        form = ContractorProfileForm(instance=profile)

    return render(
        request,
        "contractors/profile_form.html",
        {"form": form, "is_new": profile is None},
    )


@contractor_required
def project_edit(request, pk=None):
    profile = ContractorProfile.objects.filter(user=request.user).first()
    if profile is None:
        messages.error(request, "Please create your company profile first.")
        return redirect("contractors:profile_edit")

    # Ownership check: you can only open YOUR OWN projects
    project = get_object_or_404(Project, pk=pk, contractor=profile) if pk else None

    if request.method == "POST":
        form = ProjectForm(request.POST, instance=project)
        formset = ProjectImageFormSet(request.POST, request.FILES, instance=project)
        if form.is_valid() and formset.is_valid():
            saved = form.save(commit=False)
            saved.contractor = profile
            saved.save()
            formset.instance = saved
            formset.save()
            messages.success(request, "Project saved.")
            return redirect("contractors:dashboard")
    else:
        form = ProjectForm(instance=project)
        formset = ProjectImageFormSet(instance=project)

    return render(
        request,
        "contractors/project_form.html",
        {"form": form, "formset": formset, "project": project},
    )


@contractor_required
def project_delete(request, pk):
    profile = get_object_or_404(ContractorProfile, user=request.user)
    project = get_object_or_404(Project, pk=pk, contractor=profile)

    if request.method == "POST":
        project.delete()
        messages.success(request, "Project deleted.")
        return redirect("contractors:dashboard")

    return render(request, "contractors/project_confirm_delete.html", {"project": project})


# ---------------------------------------------------------------- quote requests
@client_required
def quote_request(request, pk):
    contractor = get_object_or_404(ContractorProfile.objects.filter(verified=True), pk=pk)

    # One open request per contractor: stops accidental duplicates and spam
    if QuoteRequest.objects.filter(
        client=request.user, contractor=contractor, status="pending"
    ).exists():
        messages.info(request, "You already have a pending request with this contractor.")
        return redirect("contractors:my_requests")

    if request.method == "POST":
        form = QuoteRequestForm(request.POST)
        if form.is_valid():
            quote = form.save(commit=False)
            quote.client = request.user  # set on the server, never from the browser
            quote.contractor = contractor
            quote.save()
            messages.success(request, f"Your request was sent to {contractor.company_name}.")
            return redirect("contractors:my_requests")
    else:
        form = QuoteRequestForm()

    return render(request, "contractors/quote_form.html", {"form": form, "contractor": contractor})


@client_required
def my_requests(request):
    quotes = request.user.quote_requests.select_related("contractor", "specialty")
    return render(request, "contractors/my_requests.html", {"quotes": quotes})


@contractor_required
def contractor_requests(request):
    profile = ContractorProfile.objects.filter(user=request.user).first()
    if profile is None:
        messages.error(request, "Please create your company profile first.")
        return redirect("contractors:profile_edit")
    quotes = profile.quote_requests.select_related("client", "specialty")
    return render(request, "contractors/contractor_requests.html", {"quotes": quotes})


@contractor_required
def request_respond(request, pk):
    profile = get_object_or_404(ContractorProfile, user=request.user)
    # Ownership check: you can only answer requests sent to YOU
    quote = get_object_or_404(QuoteRequest, pk=pk, contractor=profile)

    if quote.status != "pending":
        messages.info(request, "You have already answered this request.")
        return redirect("contractors:contractor_requests")

    if request.method == "POST":
        form = QuoteResponseForm(request.POST, instance=quote)
        if form.is_valid():
            form.save()
            messages.success(request, "Your reply has been sent to the client.")
            return redirect("contractors:contractor_requests")
    else:
        form = QuoteResponseForm(instance=quote)

    return render(request, "contractors/request_respond.html", {"quote": quote, "form": form})


# ---------------------------------------------------------------- reviews
@client_required
def review_edit(request, pk):
    contractor = get_object_or_404(ContractorProfile.objects.filter(verified=True), pk=pk)

    # The trust rule: no accepted request, no review
    has_accepted = QuoteRequest.objects.filter(
        client=request.user, contractor=contractor, status="accepted"
    ).exists()
    if not has_accepted:
        messages.error(request, "You can review a contractor after they accept your quote request.")
        return redirect("contractors:detail", pk=contractor.pk)

    review = Review.objects.filter(client=request.user, contractor=contractor).first()

    if request.method == "POST":
        form = ReviewForm(request.POST, instance=review)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.client = request.user
            obj.contractor = contractor
            obj.save()
            messages.success(request, "Thank you! Your review has been saved.")
            return redirect("contractors:detail", pk=contractor.pk)
    else:
        form = ReviewForm(instance=review)

    return render(
        request,
        "contractors/review_form.html",
        {"form": form, "contractor": contractor, "is_edit": review is not None},
    )
# ---------------------------------------------------------------- verification
MAX_DOCUMENTS = 8


@contractor_required
def verification(request):
    profile = ContractorProfile.objects.filter(user=request.user).first()
    if profile is None:
        messages.error(request, "Please create your company profile first.")
        return redirect("contractors:profile_edit")

    documents = profile.documents.all()

    if request.method == "POST":
        if documents.count() >= MAX_DOCUMENTS:
            messages.error(request, "You have reached the limit of 8 documents. Delete one first.")
            return redirect("contractors:verification")
        form = VerificationDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            document = form.save(commit=False)
            document.contractor = profile  # always the logged-in contractor
            document.save()
            messages.success(request, "Document uploaded. Our team will review it soon.")
            return redirect("contractors:verification")
    else:
        form = VerificationDocumentForm()

    return render(
        request,
        "contractors/verification.html",
        {"profile": profile, "documents": documents, "form": form},
    )


@contractor_required
def verification_delete(request, pk):
    profile = get_object_or_404(ContractorProfile, user=request.user)
    # Ownership check, and approved documents stay on record
    document = get_object_or_404(
        VerificationDocument, pk=pk, contractor=profile, status__in=["pending", "rejected"]
    )
    if request.method == "POST":
        document.file.delete(save=False)  # remove the file from disk too
        document.delete()
        messages.success(request, "Document deleted.")
    return redirect("contractors:verification")


@staff_member_required
def verification_file(request, pk):
    """Only Nirmaan staff can download a verification document."""
    document = get_object_or_404(VerificationDocument, pk=pk)
    return FileResponse(
        document.file.open("rb"),
        as_attachment=True,
        filename=os.path.basename(document.file.name),
    )    