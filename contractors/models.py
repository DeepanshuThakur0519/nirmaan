from uuid import uuid4

from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.storage import FileSystemStorage
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils import timezone


class Specialty(models.Model):
    """A type of construction work, e.g. 'Residential', 'Warehouse'."""
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name_plural = "specialties"
        ordering = ["name"]

    def __str__(self):
        return self.name


class ContractorProfile(models.Model):
    """The public profile of a contractor listed on Nirmaan."""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    company_name = models.CharField(max_length=200)
    city = models.CharField(max_length=100)
    about = models.TextField(blank=True)
    experience_years = models.PositiveIntegerField()
    min_budget = models.DecimalField(max_digits=12, decimal_places=2)
    max_budget = models.DecimalField(max_digits=12, decimal_places=2)
    specialties = models.ManyToManyField(Specialty, blank=True)
    verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.company_name


class Project(models.Model):
    """A completed piece of work shown in a contractor's portfolio."""
    contractor = models.ForeignKey(
        ContractorProfile, on_delete=models.CASCADE, related_name="projects"
    )
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=100, blank=True)
    specialty = models.ForeignKey(
        Specialty, null=True, blank=True, on_delete=models.SET_NULL
    )
    cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    completed_year = models.PositiveIntegerField(null=True, blank=True)
    duration_months = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-completed_year", "-created_at"]

    def __str__(self):
        return f"{self.title} ({self.contractor})"


class ProjectImage(models.Model):
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="images"
    )
    image = models.ImageField(upload_to="projects/%Y/%m/")
    caption = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return f"Image for {self.project.title}"


class Account(models.Model):
    """Extra information about a login: is this person a client or a contractor?"""
    ROLE_CHOICES = [
        ("client", "I want to build something"),
        ("contractor", "I am a contractor"),
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="account")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="client")

    def __str__(self):
        return f"{self.user.username} ({self.role})"


class QuoteRequest(models.Model):
    """A client's project brief sent to one contractor."""
    TIMELINE_CHOICES = [
        ("asap", "As soon as possible"),
        ("1_3", "Within 1 to 3 months"),
        ("3_6", "In 3 to 6 months"),
        ("6_plus", "6 months or later"),
        ("flexible", "Just exploring"),
    ]
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("declined", "Declined"),
    ]

    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name="quote_requests")
    contractor = models.ForeignKey(
        ContractorProfile, on_delete=models.CASCADE, related_name="quote_requests"
    )
    specialty = models.ForeignKey(Specialty, null=True, blank=True, on_delete=models.SET_NULL)
    location = models.CharField(max_length=100)
    budget = models.DecimalField(max_digits=12, decimal_places=2)
    timeline = models.CharField(max_length=20, choices=TIMELINE_CHOICES, default="flexible")
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    contractor_reply = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Quote from {self.client.username} to {self.contractor} ({self.status})"


class Review(models.Model):
    """A client's rating of a contractor."""
    RATING_CHOICES = [
        (5, "★★★★★  Excellent"),
        (4, "★★★★  Very good"),
        (3, "★★★  Average"),
        (2, "★★  Poor"),
        (1, "★  Terrible"),
    ]

    contractor = models.ForeignKey(
        ContractorProfile, on_delete=models.CASCADE, related_name="reviews"
    )
    client = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reviews")
    rating = models.PositiveSmallIntegerField(choices=RATING_CHOICES)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["client", "contractor"],
                name="one_review_per_client_per_contractor",
            )
        ]

    def __str__(self):
        return f"{self.client.username} rated {self.contractor} {self.rating}/5"


def get_private_storage():
    """A folder OUTSIDE media/, so it is never served by a web address."""
    return FileSystemStorage(location=settings.BASE_DIR / "private_media")


def verification_upload_path(instance, filename):
    """Store each file under a random name, never the name the user typed."""
    extension = filename.rsplit(".", 1)[-1].lower()
    return f"verification/{instance.contractor_id}/{uuid4().hex}.{extension}"


class VerificationDocument(models.Model):
    """A document a contractor uploads so Nirmaan can verify them."""
    DOC_TYPE_CHOICES = [
        ("id", "Identity proof"),
        ("licence", "Contractor licence or registration"),
        ("business", "Business registration (GST, shop licence, etc.)"),
        ("other", "Other supporting document"),
    ]
    STATUS_CHOICES = [
        ("pending", "Pending review"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    contractor = models.ForeignKey(
        ContractorProfile, on_delete=models.CASCADE, related_name="documents"
    )
    doc_type = models.CharField(max_length=20, choices=DOC_TYPE_CHOICES)
    file = models.FileField(
        upload_to=verification_upload_path,
        storage=get_private_storage,
        validators=[FileExtensionValidator(["pdf", "jpg", "jpeg", "png"])],
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    admin_note = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-uploaded_at"]

    def save(self, *args, **kwargs):
        # keep reviewed_at in step with the status
        if self.status == "pending":
            self.reviewed_at = None
        elif self.reviewed_at is None:
            self.reviewed_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_doc_type_display()} for {self.contractor} ({self.status})"