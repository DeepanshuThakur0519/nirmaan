from datetime import date

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction

from .models import Account, ContractorProfile, Project, ProjectImage


class SignUpForm(UserCreationForm):
    first_name = forms.CharField(max_length=150, label="Your name")
    email = forms.EmailField(label="Email address")
    role = forms.ChoiceField(
        choices=Account.ROLE_CHOICES,
        widget=forms.RadioSelect,
        initial="client",
        label="I am joining as",
    )

    field_order = ["role", "first_name", "email", "username", "password1", "password2"]

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "first_name", "email")

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=False)
        user.first_name = self.cleaned_data["first_name"]
        user.email = self.cleaned_data["email"]
        user.save()
        Account.objects.create(user=user, role=self.cleaned_data["role"])
        return user


class ContractorProfileForm(forms.ModelForm):
    class Meta:
        model = ContractorProfile
        # "verified" is deliberately NOT here: contractors must never verify themselves
        fields = [
            "company_name",
            "city",
            "about",
            "experience_years",
            "min_budget",
            "max_budget",
            "specialties",
        ]
        labels = {
            "company_name": "Company name",
            "about": "About your company",
            "experience_years": "Years of experience",
            "min_budget": "Smallest project you take (₹)",
            "max_budget": "Largest project you take (₹)",
            "specialties": "Types of work you do",
        }
        widgets = {
            "about": forms.Textarea(attrs={"rows": 5}),
            "specialties": forms.CheckboxSelectMultiple,
        }

    def clean(self):
        cleaned = super().clean()
        low = cleaned.get("min_budget")
        high = cleaned.get("max_budget")
        if low is not None and high is not None and low > high:
            self.add_error("max_budget", "The largest project must be at least the smallest.")
        return cleaned


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = [
            "title",
            "description",
            "location",
            "specialty",
            "cost",
            "completed_year",
            "duration_months",
        ]
        labels = {
            "title": "Project name",
            "specialty": "Type of work",
            "cost": "Project cost (₹)",
            "completed_year": "Year completed",
            "duration_months": "Duration (months)",
        }
        widgets = {"description": forms.Textarea(attrs={"rows": 4})}

    def clean_completed_year(self):
        year = self.cleaned_data.get("completed_year")
        if year is not None and not (1950 <= year <= date.today().year):
            raise forms.ValidationError("Enter a valid year.")
        return year


class ProjectImageForm(forms.ModelForm):
    class Meta:
        model = ProjectImage
        fields = ["image", "caption"]

    def clean_image(self):
        image = self.cleaned_data.get("image")
        # only check newly uploaded files, not photos already saved
        if isinstance(image, UploadedFile) and image.size > 5 * 1024 * 1024:
            raise forms.ValidationError("Each photo must be 5 MB or smaller.")
        return image


ProjectImageFormSet = forms.inlineformset_factory(
    Project,
    ProjectImage,
    form=ProjectImageForm,
    extra=3,
    can_delete=True,
    max_num=8,
)