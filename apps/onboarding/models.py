import uuid

from django.conf import settings
from django.db import models


class DocumentType(models.Model):
    CATEGORY_CHOICES = [
        ("identity", "Identity Documents"),
        ("financial", "Financial Documents"),
        ("educational", "Educational Documents"),
        ("other", "Other Documents"),
    ]

    name = models.CharField(max_length=150, unique=True)
    category = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default="other",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["category", "name"]

    def __str__(self):
        return self.name


class Joinee(models.Model):
    STATUS_CHOICES = [
        ("pre_joining", "Pre-Joining"),
        ("documents_pending", "Documents Pending"),
        ("documents_verified", "Documents Verified"),
        ("employee_code_generated", "Employee Code Generated"),
    ]

    onboarding_reference = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )
    full_name = models.CharField(max_length=150)
    personal_email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    designation = models.CharField(max_length=150, blank=True)
    department = models.CharField(max_length=150, blank=True)
    plant_location = models.CharField(max_length=150, blank=True)
    joining_date = models.DateField(null=True, blank=True)

    employee_code = models.CharField(
        max_length=100,
        blank=True,
        db_index=True,
    )
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default="pre_joining",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="created_joinees",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.full_name} - {self.onboarding_reference}"


class JoineeDocument(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("received", "Received"),
        ("verified", "Verified"),
        ("rejected", "Rejected"),
        ("not_required", "Not Required"),
    ]

    joinee = models.ForeignKey(
        Joinee,
        on_delete=models.CASCADE,
        related_name="documents",
    )
    document_type = models.ForeignKey(
        DocumentType,
        on_delete=models.PROTECT,
        related_name="joinee_documents",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
    )
    remarks = models.CharField(max_length=500, blank=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["document_type__category", "document_type__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["joinee", "document_type"],
                name="unique_joinee_document_type",
            )
        ]

    def __str__(self):
        return f"{self.joinee.full_name} - {self.document_type.name}"