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
    LEVEL_CHOICES = [
        ("L2", "L2"),
        ("L3", "L3"),
        ("L4", "L4"),
        ("L5", "L5"),
        ("L6", "L6"),
    ]

    GRADE_CHOICES = [
        ("B1", "B1"),
        ("B2", "B2"),
        ("B3", "B3"),
        ("C1", "C1"),
        ("C2", "C2"),
        ("C3", "C3"),
        ("D1", "D1"),
        ("D2", "D2"),
        ("D3", "D3"),
        ("E1", "E1"),
        ("E2", "E2"),
        ("E3", "E3"),
        ("F1", "F1"),
        ("F2", "F2"),
        ("F3", "F3"),
    ]

    level = models.CharField(
        max_length=2,
        choices=LEVEL_CHOICES,
        blank=True,
    )
    grade = models.CharField(
        max_length=2,
        choices=GRADE_CHOICES,
        blank=True,
    )
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


class JoiningKitRequest(models.Model):
    STATUS_CHOICES = [
        ("pending", "Awaiting Manager Response"),
        ("submitted", "Submitted by Manager"),
        ("in_progress", "In Progress"),
        ("fulfilled", "Fulfilled"),
    ]

    ASSET_CHOICES = [
        ("laptop", "Laptop"),
        ("desktop", "Desktop Computer"),
        ("monitor", "Monitor"),
        ("keyboard_mouse", "Keyboard and Mouse"),
        ("headset", "Headset"),
        ("mobile", "Mobile Phone"),
        ("sim", "SIM Card"),
        ("tablet", "Tablet"),
        ("email", "Email Account"),
        ("sap", "ERP / SAP Access"),
        ("peoplestrong", "PeopleStrong Access"),
        ("software", "Software / Licences"),
        ("access_card", "Access Card"),
        ("safety_shoes", "Safety Shoes"),
        ("helmet", "Safety Helmet"),
        ("safety_glasses", "Safety Glasses"),
        ("uniform", "Uniform"),
        ("other_ppe", "Other PPE / Safety Kit"),
        ("desk_chair", "Office Desk and Chair"),
        ("tools", "Job-Specific Tools"),
        ("other", "Other Asset"),
    ]

    joinee = models.ForeignKey(
        "Joinee",
        on_delete=models.CASCADE,
        related_name="joining_kit_requests",
    )
    manager_email = models.EmailField(
        default="abhishek.chuiya@vishakha.com"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
    )
    selected_assets = models.JSONField(default=list, blank=True)
    required_by = models.CharField(
        max_length=40,
        default="Before joining date",
    )
    notes = models.TextField(blank=True)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="joining_kit_requests_created",
    )
    manager_submitted_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"Joining Kit - {self.joinee.full_name} "
            f"({self.joinee.employee_code})"
        )




class JoiningKitTicket(models.Model):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("creating", "Creating"),
        ("created", "Created"),
        ("failed", "Failed"),
    ]

    joining_kit_request = models.ForeignKey(
        "JoiningKitRequest",
        on_delete=models.CASCADE,
        related_name="generated_tickets",
    )
    asset_key = models.CharField(max_length=50)
    asset_label = models.CharField(max_length=150)
    ticket_number = models.CharField(max_length=100, blank=True)
    ticket_id = models.CharField(max_length=100, blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
    )
    error_message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["joining_kit_request", "asset_key"],
                name="unique_joining_kit_asset_ticket",
            )
        ]

    def __str__(self):
        return (
            f"{self.asset_label} - "
            f"{self.ticket_number or self.status}"
        )
