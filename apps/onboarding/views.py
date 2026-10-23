from django.utils import timezone
from .models import JoiningKitRequest

from datetime import datetime
from io import BytesIO

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import HttpResponse, request
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.shortcuts import redirect, render
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

from .models import (
    DocumentType,
    Joinee,
    JoineeDocument,
    JoiningKitRequest,
)

HR_EMAIL = "niranshu.mittal@vishakha.com"
MANAGER_EMAIL = "abhishek.chuiya@vishakha.com"


def is_hr_user(user):
    return (
        user.is_authenticated
        and user.is_active
        and user.is_staff
        and user.email.strip().lower() == HR_EMAIL
    )


def is_joining_kit_manager(user):
    return (
        user.is_authenticated
        and user.is_active
        and user.email.strip().lower() == MANAGER_EMAIL
    )


def require_hr(user):
    if not is_hr_user(user):
        raise PermissionDenied(
            "Only the authorized HR user can perform this action."
        )


def require_assigned_manager(user, joining_kit_request):
    if not is_joining_kit_manager(user):
        raise PermissionDenied(
            "You are not authorized to access manager requests."
        )

    if (
        joining_kit_request.manager_email.strip().lower()
        != user.email.strip().lower()
    ):
        raise PermissionDenied(
            "This Joining Kit request is not assigned to you."
        )

    
DEFAULT_DOCUMENTS = [
    ("Aadhaar Card", "identity"),
    ("PAN Card", "identity"),
    ("Voter ID", "identity"),
    ("Bank Details", "financial"),
    ("IFSC Code", "financial"),
    ("Account Number", "financial"),
    ("Passbook Image", "financial"),
    ("10th Marksheet", "educational"),
    ("12th Marksheet", "educational"),
    ("Degree Certificate", "educational"),
]


def seed_default_documents():
    for name, category in DEFAULT_DOCUMENTS:
        DocumentType.objects.get_or_create(
            name=name,
            defaults={"category": category, "is_active": True},
        )


def ensure_joinee_documents(joinee):
    """Add active requirements that are missing for this joinee."""
    for document_type in DocumentType.objects.filter(is_active=True):
        JoineeDocument.objects.get_or_create(
            joinee=joinee,
            document_type=document_type,
        )


def refresh_joinee_status(joinee):
    documents = list(joinee.documents.all())

    if joinee.employee_code.strip():
        status = "employee_code_generated"
    elif documents and all(
        doc.status in ("verified", "not_required")
        for doc in documents
    ):
        status = "documents_verified"
    elif any(
        doc.status in ("pending", "rejected")
        for doc in documents
    ):
        status = "documents_pending"
    else:
        status = "pre_joining"

    if joinee.status != status:
        joinee.status = status
        joinee.save(update_fields=["status", "updated_at"])


def prepare_joinee(joinee):
    """Ensure the checklist exists and refresh its overall status."""
    ensure_joinee_documents(joinee)
    refresh_joinee_status(joinee)


@login_required
def dashboard(request):

    if request.user.email.strip().lower() == "abhishek.chuiya@vishakha.com":
        return redirect("onboarding:manager_joining_kit_dashboard")

    if not (
            request.user.is_staff
            and request.user.email.strip().lower()
            == "niranshu.mittal@vishakha.com"
        ):
        raise PermissionDenied(
            "You are not authorized to access the HR onboarding dashboard."
        )

    seed_default_documents()

    # Create any newly added requirements for existing joinees.
    for joinee in Joinee.objects.all():
        prepare_joinee(joinee)

    joinees = list(
        Joinee.objects.prefetch_related(
            "documents__document_type"
        ).all()
    )

    for joinee in joinees:
        applicable = [
            doc for doc in joinee.documents.all()
            if doc.status != "not_required"
        ]
        joinee.document_total = len(applicable)
        joinee.document_completed = sum(
            doc.status == "verified" for doc in applicable
        )
        joinee.document_pending = sum(
            doc.status in ("pending", "rejected")
            for doc in applicable
        )

    return render(
        request,
        "onboarding/dashboard.html",
        {
            "joinees": joinees,
            "document_types": DocumentType.objects.filter(
                is_active=True
            ),
            "total": Joinee.objects.count(),
            "code_generated": Joinee.objects.exclude(
                employee_code=""
            ).count(),
            "verified": Joinee.objects.filter(
                status="documents_verified"
            ).count(),
            "pending": Joinee.objects.filter(
                status="documents_pending"
            ).count(),
        },
    )


@login_required
@require_POST
def add_joinee(request):
    seed_default_documents()

    full_name = request.POST.get("full_name", "").strip()
    if not full_name:
        return HttpResponse("Full Name is required.", status=400)

    joining_date = request.POST.get("joining_date") or None
    if joining_date:
        try:
            datetime.strptime(joining_date, "%Y-%m-%d")
        except ValueError:
            return HttpResponse("Invalid joining date.", status=400)

    with transaction.atomic():
        joinee = Joinee.objects.create(
            full_name=full_name,
            personal_email=request.POST.get(
                "personal_email", ""
            ).strip(),
            phone=request.POST.get("phone", "").strip(),
            designation=request.POST.get("designation", "").strip(),
            level=request.POST.get("level", "").strip().upper(),
            grade=request.POST.get("grade", "").strip().upper(),
            department=request.POST.get("department", "").strip(),
            plant_location=request.POST.get(
                "plant_location", ""
            ).strip(),
            joining_date=joining_date,
            created_by=request.user,
        )
        prepare_joinee(joinee)

    return redirect("onboarding:dashboard")


@login_required
@require_POST
def update_document(request, document_id):
    document = get_object_or_404(
        JoineeDocument.objects.select_related("joinee"),
        pk=document_id,
    )

    allowed_statuses = {
        value for value, label in JoineeDocument.STATUS_CHOICES
    }
    new_status = request.POST.get("status", "")

    if new_status not in allowed_statuses:
        return HttpResponse("Invalid document status.", status=400)

    document.status = new_status
    document.remarks = request.POST.get("remarks", "").strip()[:500]
    document.updated_by = request.user
    document.save()

    refresh_joinee_status(document.joinee)

    return redirect(
        "onboarding:joinee_detail",
        joinee_id=document.joinee_id,
    )


@login_required
@require_POST
def add_document_type(request):
    name = request.POST.get("name", "").strip()
    category = request.POST.get("category", "other").strip()

    valid_categories = {
        value for value, label in DocumentType.CATEGORY_CHOICES
    }

    if not name:
        return HttpResponse("Document name is required.", status=400)

    if category not in valid_categories:
        return HttpResponse("Invalid document category.", status=400)

    with transaction.atomic():
        document_type, _ = DocumentType.objects.get_or_create(
            name=name,
            defaults={"category": category, "is_active": True},
        )

        if not document_type.is_active:
            document_type.is_active = True

        document_type.category = category
        document_type.save(update_fields=["is_active", "category"])

        # Add this requirement to every existing joinee.
        for joinee in Joinee.objects.all():
            JoineeDocument.objects.get_or_create(
                joinee=joinee,
                document_type=document_type,
            )

    return redirect("onboarding:dashboard")


@login_required
@require_POST
def update_employee_code(request, joinee_id):
    joinee = get_object_or_404(Joinee, pk=joinee_id)
    employee_code = request.POST.get("employee_code", "").strip()

    if employee_code:
        duplicate = Joinee.objects.filter(
            employee_code=employee_code
        ).exclude(pk=joinee.pk).exists()

        if duplicate:
            return HttpResponse(
                "This Employee Code is already assigned to another joinee.",
                status=400,
            )

    joinee.employee_code = employee_code
    joinee.save(update_fields=["employee_code", "updated_at"])
    refresh_joinee_status(joinee)

    return redirect(
        "onboarding:joinee_detail",
        joinee_id=joinee.pk,
    )


@login_required
def joinee_detail(request, joinee_id):
    joinee = get_object_or_404(Joinee, pk=joinee_id)

    prepare_joinee(joinee)

    documents = list(
        joinee.documents.select_related(
            "document_type",
            "updated_by",
        ).all()
    )

    applicable_documents = [
        doc for doc in documents
        if doc.status != "not_required"
    ]
    completed_documents = sum(
        doc.status == "verified"
        for doc in applicable_documents
    )
    total_documents = len(applicable_documents)

    progress = (
        round(completed_documents * 100 / total_documents)
        if total_documents
        else 0
    )

    return render(
        request,
        "onboarding/joinee_detail.html",
        {
            "joinee": joinee,
            "documents": documents,
            "document_status_choices": JoineeDocument.STATUS_CHOICES,
            "total_documents": total_documents,
            "completed_documents": completed_documents,
            "progress": progress,
        },
    )


@login_required
def export_excel(request):
    seed_default_documents()

    joinees = list(
        Joinee.objects.prefetch_related(
            "documents__document_type"
        ).all()
    )

    for joinee in joinees:
        prepare_joinee(joinee)

    workbook = Workbook()
    summary = workbook.active
    summary.title = "Pre-Joining Tracker"

    summary.append([
        "Onboarding Reference",
        "Full Name",
        "Personal Email",
        "Phone",
        "Designation",
        "Department",
        "Plant / Location",
        "Joining Date",
        "Employee Code",
        "Overall Status",
        "Created At",
    ])

    details = workbook.create_sheet("Document Statuses")
    details.append([
        "Onboarding Reference",
        "Full Name",
        "Employee Code",
        "Document Category",
        "Document Name",
        "Document Status",
        "Remarks",
        "Last Updated",
    ])

    for joinee in joinees:
        summary.append([
            str(joinee.onboarding_reference),
            joinee.full_name,
            joinee.personal_email,
            joinee.phone,
            joinee.designation,
            joinee.department,
            joinee.plant_location,
            joinee.joining_date.isoformat()
            if joinee.joining_date else "",
            joinee.employee_code,
            joinee.get_status_display(),
            joinee.created_at.strftime("%Y-%m-%d %H:%M"),
        ])

        for doc in joinee.documents.all():
            details.append([
                str(joinee.onboarding_reference),
                joinee.full_name,
                joinee.employee_code,
                doc.document_type.get_category_display(),
                doc.document_type.name,
                doc.get_status_display(),
                doc.remarks,
                doc.updated_at.strftime("%Y-%m-%d %H:%M"),
            ])

    for sheet in workbook.worksheets:
        sheet.freeze_panes = "A2"
        sheet.auto_filter.ref = sheet.dimensions

        for cell in sheet[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill(
                fill_type="solid",
                fgColor="17365D",
            )

        for column_cells in sheet.columns:
            max_length = max(
                len(str(cell.value or ""))
                for cell in column_cells
            )
            sheet.column_dimensions[
                get_column_letter(column_cells[0].column)
            ].width = min(max(max_length + 2, 14), 38)

    output = BytesIO()
    workbook.save(output)
    output.seek(0)

    response = HttpResponse(
        output.getvalue(),
        content_type=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
    )
    response["Content-Disposition"] = (
        'attachment; filename="Vishakha_PreJoining_Tracker.xlsx"'
    )
    return response

ASSET_OPTIONS = [
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
# Department-specific computer eligibility.
# "yes" means recommend a laptop by default.
# "no" means do not preselect a computer.
# "need_base" means the manager must decide.

DEPARTMENT_COMPUTER_RULES = {
    "ADMINISTRATION": "yes",
    "ENVIRONMENT HEALTH & SAFETY": "need_base",
    "ANODIZING": "no",
    "ASSEMBLY": "no",
    "PROCESS AUDIT": "yes",
    "BUSINESS DEVELOPMENT": "yes",
    "BUSINESS / OPERATIONAL EXCELLENCE": "yes",
    "CIVIL": "no",
    "CONVERTING": "no",
    "CORPORATE AFFAIRS": "yes",
    "CORPORATE COMMUNICATION": "yes",
    "HUMAN RESOURCE": "yes",
    "INFORMATION TECHNOLOGY": "yes",
    "CORPORATE PROCUREMENT": "yes",
    "TRAVEL DESK": "yes",
    "DATA ANALYTICS": "yes",
    "DEEP PROCESS": "no",
    "DESIGN": "yes",
    "DIRECTOR'S OFFICE": "yes",
    "DISPATCH": "need_base",
    "ENGINEERING": "no",
    "EXIM": "yes",
    "EXTRUSION": "no",
    "FINANCE/ACCOUNTS": "yes",
    "FURNACE/FOUNDRY": "no",
    "GRAPHICS": "yes",
    "LAMINATION": "no",
    "LEGAL": "yes",
    "LOGISTIC": "yes",
    "MACHINE SHOP": "no",
    "MANAGEMENT AUDIT/ASSURANCE SERVICES": "yes",
    "MOULDING": "no",
    "MR & DOCUMENTATION": "yes",
    "NEW PRODUCT DEVELOPMENT": "yes",
    "OPERATIONS": "yes",
    "PE": "no",
    "PLANNING/STRATEGY": "yes",
    "EXPORT": "yes",
    "POUCH": "no",
    "PRINTING": "no",
    "PROCUREMENT": "yes",
    "PRODUCTION": "no",
    "PRODUCTION PLANNING & CONTROL": "yes",
    "PROJECT PLANNING & CONTROL": "yes",
    "PROJECTS": "no",
    "SUPPLY CHAIN MANAGEMENT": "need_base",
    "PROJECTS CIVIL & STRUCTURE": "need_base",
    "QUALITY CONTROL": "no",
    "PVC": "no",
    "QAME": "no",
    "RECYCLING": "no",
    "RESEARCH DEVELOPMENT": "yes",
    "REWINDING": "no",
    "RM PROCUREMENT": "yes",
    "ROLLED GLASS": "no",
    "SALES & MARKETING": "yes",
    "SAND": "no",
    "SECRETARIAL": "yes",
    "SECURITY": "no",
    "SLITTING": "no",
    "STORES": "need_base",
    "TOOL ROOM": "no",
}


def get_recommended_assets(joinee):
    """
    Return default asset keys for a joinee.
    These are recommendations only; the manager may change them.
    """
    level = (joinee.level or "").strip().upper()
    grade = (joinee.grade or "").strip().upper()
    department = " ".join(
        (joinee.department or "").upper().replace("\u00a0", " ").split()
    )

    computer_rule = DEPARTMENT_COMPUTER_RULES.get(
        department,
        "need_base",
    )

    recommended = []

    # L2, L3 and L4-D1 have standard laptop and email defaults.
    if level in ("L2", "L3") or (
        level == "L4" and grade == "D1"
    ):
        recommended.extend(["laptop", "email"])

    # L4-D2/D3 and all L5/L6 use department computer rules.
    elif (
        (level == "L4" and grade in ("D2", "D3"))
        or level in ("L5", "L6")
    ):
        if computer_rule == "yes":
            recommended.append("laptop")

        # Email is only auto-recommended for Support departments
        # in L5/L6; production email exceptions are not specified yet.
        if level == "L4" or (
            level in ("L5", "L6")
            and computer_rule == "yes"
        ):
            recommended.append("email")

    # Do not preselect desktop alongside laptop.
    # Manager can still select Desktop or any other available asset.
    return recommended

# @login_required
# @require_POST
# def create_joining_kit_request(request, joinee_id):
#     joinee = get_object_or_404(Joinee, pk=joinee_id)

#     if not joinee.employee_code.strip():
#         return HttpResponse(
#             "Enter the Employee Code before creating a Joining Kit request.",
#             status=400,
#         )

#     # Avoid creating another open request for the same joinee.
#     existing = JoiningKitRequest.objects.filter(
#         joinee=joinee,
#         status__in=["pending", "submitted", "in_progress"],
#     ).first()

#     if existing:
#         return redirect(
#             "onboarding:joining_kit_detail",
#             request_id=existing.pk,
#         )

#     kit_request = JoiningKitRequest.objects.create(
#         joinee=joinee,
#         manager_email="abhishek.chuiya@vishakha.com",
#         requested_by=request.user,
#     )

#     return redirect(
#         "onboarding:joining_kit_detail",
#         request_id=kit_request.pk,
#     )


@login_required
@require_POST
def create_joining_kit_request(request, joinee_id):
    require_hr(request.user)

    # The user must explicitly select the Joining Kit trigger.
    if request.POST.get("trigger_joining_kit") != "yes":
        raise PermissionDenied(
            "The Joining Kit trigger was not selected."
        )

    joinee = get_object_or_404(Joinee, pk=joinee_id)

    if not joinee.employee_code.strip():
        return HttpResponse(
            "Generate and save the employee code before creating "
            "a Joining Kit request.",
            status=400,
        )

    existing_request = JoiningKitRequest.objects.filter(
        joinee=joinee,
        status__in=["pending", "submitted", "in_progress"],
    ).first()

    if existing_request:
        return redirect(
            "onboarding:joining_kit_detail",
            request_id=existing_request.pk,
        )

    joining_kit_request = JoiningKitRequest.objects.create(
        joinee=joinee,
        manager_email=MANAGER_EMAIL,
        status="pending",
        requested_by=request.user,
    )

    return redirect(
        "onboarding:joining_kit_detail",
        request_id=joining_kit_request.pk,
    )
@login_required
def manager_joining_kit_dashboard(request):
    if not is_joining_kit_manager(request.user):
        raise PermissionDenied(
            "Only the assigned Joining Kit manager can access this dashboard."
        )

    joining_kit_requests = (
        JoiningKitRequest.objects
        .filter(manager_email__iexact=request.user.email)
        .select_related("joinee", "requested_by")
        .order_by("-created_at")
    )

    return render(
        request,
        "onboarding/manager_joining_kit_dashboard.html",
        {
            "joining_kit_requests": joining_kit_requests,
        },
    )


# @login_required
# def joining_kit_detail(request, request_id):
#     kit_request = get_object_or_404(
#         JoiningKitRequest.objects.select_related(
#             "joinee",
#             "requested_by",
#         ),
#         pk=request_id,
#     )

#     if request.method == "POST":
#         if kit_request.status != "pending":
#             return HttpResponse(
#                 "This request has already been submitted or processed.",
#                 status=400,
#             )

#         selected = request.POST.getlist("assets")
#         valid_assets = {key for key, label in ASSET_OPTIONS}
#         selected = list(dict.fromkeys(
#             item for item in selected if item in valid_assets
#         ))

#         if not selected:
#             return render(
#                 request,
#                 "onboarding/joining_kit_detail.html",
#                 {
#                     "kit_request": kit_request,
#                     "asset_options": ASSET_OPTIONS,
#                     "error": "Select at least one asset before submitting.",
#                 },
#                 status=400,
#             )

#         kit_request.selected_assets = selected
#         kit_request.required_by = request.POST.get(
#             "required_by",
#             "Before joining date",
#         )
#         kit_request.notes = request.POST.get("notes", "").strip()[:3000]
#         kit_request.status = "submitted"
#         kit_request.manager_submitted_at = timezone.now()
#         kit_request.save(
#             update_fields=[
#                 "selected_assets",
#                 "required_by",
#                 "notes",
#                 "status",
#                 "manager_submitted_at",
#                 "updated_at",
#             ]
#         )

#         return redirect(
#             "onboarding:joining_kit_detail",
#             request_id=kit_request.pk,
#         )

#     selected_labels = [
#         label
#         for key, label in ASSET_OPTIONS
#         if key in kit_request.selected_assets
#     ]

#     return render(
#         request,
#         "onboarding/joining_kit_detail.html",
#         {
#             "kit_request": kit_request,
#             "asset_options": ASSET_OPTIONS,
#             "selected_labels": selected_labels,
#         },
#     )

@login_required
def joining_kit_detail(request, request_id):
    joining_kit_request = get_object_or_404(
        JoiningKitRequest.objects.select_related(
            "joinee",
            "requested_by",
        ),
        pk=request_id,
    )

    is_manager = is_joining_kit_manager(request.user)
    is_hr = is_hr_user(request.user)

    if not (is_manager or is_hr):
        raise PermissionDenied(
            "You are not authorized to access this request."
        )

    if is_manager:
        require_assigned_manager(request.user, joining_kit_request)

    if request.method == "POST":
        # HR is strictly read-only on this page.
        if not is_manager:
            raise PermissionDenied(
                "HR can view the request but cannot submit manager selections."
            )

        if joining_kit_request.status != "pending":
            return HttpResponse(
                "This request has already been submitted or is no longer editable.",
                status=400,
            )


        selected_assets = request.POST.getlist("selected_assets")

        # Build the allowed asset identifiers from the configured options.
        valid_asset_values = {
            str(value).strip()
            for value, label in ASSET_OPTIONS
        }

        # Normalize submitted values and remove duplicate selections.
        selected_assets = list(dict.fromkeys(
            asset.strip()
            for asset in selected_assets
            if asset.strip()
        ))

        # Validate every selected asset against the configured options.
        invalid_assets = [
            asset for asset in selected_assets
            if asset not in valid_asset_values
        ]

        if invalid_assets:
            return HttpResponse(
                "DEBUG - Invalid asset values received: "
                f"{invalid_assets!r}. "
                f"Allowed values: {sorted(valid_asset_values)!r}",
                status=400,
            )

        joining_kit_request.selected_assets = selected_assets
        joining_kit_request.required_by = (
            request.POST.get("required_by", "Before joining date").strip()[:100]
            or "Before joining date"
        )
        joining_kit_request.notes = (
            request.POST.get("notes", "").strip()[:2000]
        )
        joining_kit_request.status = "submitted"
        joining_kit_request.manager_submitted_at = timezone.now()

        joining_kit_request.save(
            update_fields=[
                "selected_assets",
                "required_by",
                "notes",
                "status",
                "manager_submitted_at",
                "updated_at",
            ]
        )

        return redirect(
            "onboarding:joining_kit_detail",
            request_id=joining_kit_request.pk,
        )


    return render(
        request,
        "onboarding/joining_kit_detail.html",
        {
            "joining_kit_request": joining_kit_request,
            "asset_options": ASSET_OPTIONS,
            "recommended_assets": get_recommended_assets(
                joining_kit_request.joinee
            ),
            "can_edit": (
                is_manager
                and joining_kit_request.status == "pending"
            ),
            "is_hr_view": is_hr,
        },
    )