from django.contrib import admin

from .models import DocumentType, Joinee, JoineeDocument


@admin.register(DocumentType)
class DocumentTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "is_active", "created_at")
    list_filter = ("category", "is_active")
    search_fields = ("name",)


class JoineeDocumentInline(admin.TabularInline):
    model = JoineeDocument
    extra = 0
    readonly_fields = ("updated_at",)


@admin.register(Joinee)
class JoineeAdmin(admin.ModelAdmin):
    list_display = (
        "full_name",
        "employee_code",
        "department",
        "plant_location",
        "status",
        "joining_date",
    )
    list_filter = ("status", "department", "plant_location")
    search_fields = (
        "full_name",
        "personal_email",
        "employee_code",
    )
    inlines = [JoineeDocumentInline]


@admin.register(JoineeDocument)
class JoineeDocumentAdmin(admin.ModelAdmin):
    list_display = (
        "joinee",
        "document_type",
        "status",
        "updated_by",
        "updated_at",
    )
    list_filter = ("status", "document_type__category")
    search_fields = ("joinee__full_name", "document_type__name")