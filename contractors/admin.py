from django.contrib import admin

from .models import Account, ContractorProfile, Project, ProjectImage, QuoteRequest, Review, Specialty

admin.site.site_header = "Nirmaan Admin"
admin.site.site_title = "Nirmaan"
admin.site.index_title = "Manage Nirmaan"


@admin.register(Specialty)
class SpecialtyAdmin(admin.ModelAdmin):
    search_fields = ["name"]


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ["user", "role"]
    list_filter = ["role"]
    search_fields = ["user__username", "user__email"]


@admin.register(ContractorProfile)
class ContractorProfileAdmin(admin.ModelAdmin):
    list_display = ["company_name", "city", "experience_years", "verified", "created_at"]
    list_filter = ["verified", "city", "specialties"]
    search_fields = ["company_name", "city", "user__username"]
    actions = ["mark_verified"]

    @admin.action(description="Mark selected contractors as verified")
    def mark_verified(self, request, queryset):
        updated = queryset.update(verified=True)
        self.message_user(request, f"{updated} contractor(s) marked as verified.")


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