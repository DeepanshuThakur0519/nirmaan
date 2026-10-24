from django.contrib import admin, messages
from django.urls import reverse
from django.utils.html import format_html

from .models import (
    Account,
    ContractorProfile,
    Project,
    ProjectImage,
    QuoteRequest,
    Review,
    Specialty,
    VerificationDocument,
)

admin.site.site_header = "Nirmaan Admin"
admin.site.site_title = "Nirmaan"
admin.site.index_title = "Manage Nirmaan"

# A contractor needs an approved identity proof AND an approved licence or business registration
LICENCE_TYPES = {"licence", "business"}


def documents_ok(profile):
    approved = set(
        profile.documents.filter(status="approved").values_list("doc_type", flat=True)
    )
    return "id" in approved and bool(approved & LICENCE_TYPES)


def file_link(obj):
    if not obj.pk:
        return "-"
    url = reverse("contractors:verification_file", args=[obj.pk])
    return format_html('<a href="{}" target="_blank">Download file</a>', url)


@admin.register(Specialty)
class SpecialtyAdmin(admin.ModelAdmin):
    search_fields = ["name"]


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ["user", "role"]
    list_filter = ["role"]
    search_fields = ["user__username", "user__email"]


class VerificationDocumentInline(admin.TabularInline):
    model = VerificationDocument
    extra = 0
    can_delete = False
    fields = ["doc_type", "document_file", "status", "admin_note", "uploaded_at"]
    readonly_fields = ["doc_type", "document_file", "uploaded_at"]

    @admin.display(description="File")
    def document_file(self, obj):
        return file_link(obj)

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(ContractorProfile)
class ContractorProfileAdmin(admin.ModelAdmin):
    list_display = ["company_name", "city", "experience_years", "verified", "documents_ready", "created_at"]
    list_filter = ["verified", "city", "specialties"]
    search_fields = ["company_name", "city", "user__username"]
    # "verified" can only be changed with the actions below, never by ticking a box
    readonly_fields = ["verified"]
    inlines = [VerificationDocumentInline]
    actions = ["verify_selected", "revoke_verification"]

    @admin.display(boolean=True, description="Documents OK")
    def documents_ready(self, obj):
        return documents_ok(obj)

    @admin.action(description="Verify selected contractors (needs approved documents)")
    def verify_selected(self, request, queryset):
        verified = skipped = 0
        for profile in queryset:
            if documents_ok(profile):
                profile.verified = True
                profile.save(update_fields=["verified"])
                verified += 1
            else:
                skipped += 1
        if verified:
            self.message_user(request, f"{verified} contractor(s) verified.")
        if skipped:
            self.message_user(
                request,
                f"{skipped} contractor(s) skipped: they need an approved identity proof "
                "and an approved licence or business registration.",
                level=messages.WARNING,
            )

    @admin.action(description="Revoke verification of selected contractors")
    def revoke_verification(self, request, queryset):
        updated = queryset.update(verified=False)
        self.message_user(request, f"{updated} contractor(s) are no longer verified.")


@admin.register(VerificationDocument)
class VerificationDocumentAdmin(admin.ModelAdmin):
    list_display = ["contractor", "doc_type", "status", "uploaded_at", "download"]
    list_filter = ["status", "doc_type"]
    search_fields = ["contractor__company_name", "contractor__user__username"]
    fields = ["contractor", "doc_type", "download", "status", "admin_note", "uploaded_at", "reviewed_at"]
    readonly_fields = ["contractor", "doc_type", "download", "uploaded_at", "reviewed_at"]
    actions = ["approve_selected", "reject_selected"]

    @admin.display(description="File")
    def download(self, obj):
        return file_link(obj)

    def has_add_permission(self, request):
        return False

    @admin.action(description="Approve selected documents")
    def approve_selected(self, request, queryset):
        for document in queryset:
            document.status = "approved"
            document.save()
        self.message_user(request, f"{queryset.count()} document(s) approved.")

    @admin.action(description="Reject selected documents")
    def reject_selected(self, request, queryset):
        for document in queryset:
            document.status = "rejected"
            document.save()
        self.message_user(
            request,
            f"{queryset.count()} document(s) rejected. Open a document to write the reason.",
        )


class ProjectImageInline(admin.TabularInline):
    model = ProjectImage
    extra = 3


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ["title", "contractor", "location", "completed_year", "cost"]
    list_filter = ["completed_year", "specialty"]
    search_fields = ["title", "contractor__company_name"]
    inlines = [ProjectImageInline]


@admin.register(QuoteRequest)
class QuoteRequestAdmin(admin.ModelAdmin):
    list_display = ["client", "contractor", "budget", "status", "created_at"]
    list_filter = ["status", "timeline"]
    search_fields = ["client__username", "contractor__company_name", "description"]


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ["contractor", "client", "rating", "created_at"]
    list_filter = ["rating"]
    search_fields = ["contractor__company_name", "client__username", "comment"]   