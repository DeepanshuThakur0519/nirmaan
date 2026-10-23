from decimal import Decimal, InvalidOperation
from functools import wraps

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import ContractorProfileForm, ProjectForm, ProjectImageFormSet, SignUpForm
from .models import ContractorProfile, Project, Specialty


# ---------------------------------------------------------------- access control
def contractor_required(view_func):
    """Allow only logged-in users whose account role is 'contractor'."""

    @login_required
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        account = getattr(request.user, "account", None)
        if account is None or account.role != "contractor":
            messages.error(request, "That page is only for contractor accounts.")
            return redirect("contractors:home")
        return view_func(request, *args, **kwargs)

    return wrapper


# ---------------------------------------------------------------- public pages
def home(request):
    verified = ContractorProfile.objects.filter(verified=True)
    featured = verified.prefetch_related("specialties")[:6]
    context = {
        "featured": featured,
        "verified_count": verified.count(),
        "city_count": verified.values("city").distinct().count(),
        "specialty_count": Specialty.objects.count(),
    }
    return render(request, "contractors/home.html", context)


def contractor_list(request):
    contractors = ContractorProfile.objects.filter(verified=True).prefetch_related("specialties")

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
    queryset = ContractorProfile.objects.filter(verified=True).prefetch_related("specialties")
    contractor = get_object_or_404(queryset, pk=pk)
    projects = contractor.projects.select_related("specialty").prefetch_related("images")
    return render(
        request,
        "contractors/detail.html",
        {"contractor": contractor, "projects": projects},
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
    if profile:
        projects = profile.projects.select_related("specialty").prefetch_related("images")
    return render(
        request,
        "contractors/dashboard.html",
        {"profile": profile, "projects": projects},
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
    