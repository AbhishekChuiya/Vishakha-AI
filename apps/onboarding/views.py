# from datetime import datetime
# from io import BytesIO

# from django.contrib.auth.decorators import login_required
# from django.db import transaction
# from django.http import HttpResponse
# from django.shortcuts import get_object_or_404, redirect, render
# from django.views.decorators.http import require_POST

# from openpyxl import Workbook
# from openpyxl.styles import Font, PatternFill
# from openpyxl.utils import get_column_letter

# from .models import DocumentType, Joinee, JoineeDocument


# DEFAULT_DOCUMENTS = [
#     ("Aadhaar Card", "identity"),
#     ("PAN Card", "identity"),
#     ("Voter ID", "identity"),
#     ("Bank Details", "financial"),
#     ("IFSC Code", "financial"),
#     ("Account Number", "financial"),
#     ("Passbook Image", "financial"),
#     ("10th Marksheet", "educational"),
#     ("12th Marksheet", "educational"),
#     ("Degree Certificate", "educational"),
# ]


# def seed_default_documents():
#     for name, category in DEFAULT_DOCUMENTS:
#         DocumentType.objects.get_or_create(
#             name=name,
#             defaults={"category": category, "is_active": True},
#         )


# def ensure_joinee_documents(joinee):
#     """Create any newly configured document requirements for this joinee."""
#     active_types = DocumentType.objects.filter(is_active=True)

#     for document_type in active_types:
#         JoineeDocument.objects.get_or_create(
#             joinee=joinee,
#             document_type=document_type,
#         )


# def refresh_joinee_status(joinee):
#     documents = list(
#         JoineeDocument.objects.filter(joinee=joinee)
#     )

#     if joinee.employee_code.strip():
#         joinee.status = "employee_code_generated"
#     elif documents and all(
#         doc.status in ("verified", "not_required")
#         for doc in documents
#     ):
#         joinee.status = "documents_verified"
#     elif any(
#         doc.status in ("pending", "rejected")
#         for doc in documents
#     ):
#         joinee.status = "documents_pending"
#     else:
#         joinee.status = "pre_joining"

#     joinee.save(update_fields=["status", "updated_at"])

# @login_required
# def dashboard(request):
#     seed_default_documents()

#     # Ensure all active requirements exist for every joinee.
#     for joinee in Joinee.objects.all():
#         ensure_joinee_documents(joinee)
#         refresh_joinee_status(joinee)

#     # Re-query so newly created document records are included.
#     joinees = Joinee.objects.prefetch_related(
#         "documents__document_type"
#     )

#     document_types = DocumentType.objects.filter(is_active=True)

#     return render(
#         request,
#         "onboarding/dashboard.html",
#         {
#             "joinees": joinees,
#             "documents": documents,
#             "document_types": document_types,
#             "document_status_choices": JoineeDocument.STATUS_CHOICES,
#             "total_documents": total_documents,
#             "total": Joinee.objects.count(),
#             "code_generated": Joinee.objects.exclude(
#                 employee_code=""
#             ).count(),
#             "verified": Joinee.objects.filter(
#                 status="documents_verified"
#             ).count(),
#             "pending": Joinee.objects.filter(
#                 status="documents_pending"
#             ).count(),
#         },
#     )



# @login_required
# @require_POST
# def add_joinee(request):
#     seed_default_documents()

#     full_name = request.POST.get("full_name", "").strip()
#     if not full_name:
#         return redirect("onboarding:dashboard")

#     joining_date = request.POST.get("joining_date") or None
#     if joining_date:
#         try:
#             datetime.strptime(joining_date, "%Y-%m-%d")
#         except ValueError:
#             joining_date = None

#     with transaction.atomic():
#         joinee = Joinee.objects.create(
#             full_name=full_name,
#             personal_email=request.POST.get("personal_email", "").strip(),
#             phone=request.POST.get("phone", "").strip(),
#             designation=request.POST.get("designation", "").strip(),
#             department=request.POST.get("department", "").strip(),
#             plant_location=request.POST.get("plant_location", "").strip(),
#             joining_date=joining_date,
#             created_by=request.user,
#         )
#         ensure_joinee_documents(joinee)
#         refresh_joinee_status(joinee)

#     return redirect("onboarding:dashboard")


# @login_required
# @require_POST
# def update_document(request, document_id):
#     document = get_object_or_404(
#         JoineeDocument.objects.select_related("joinee"),
#         pk=document_id,
#     )

#     allowed_statuses = {
#         value for value, label in JoineeDocument.STATUS_CHOICES
#     }
#     new_status = request.POST.get("status", "")

#     if new_status in allowed_statuses:
#         document.status = new_status
#         document.remarks = request.POST.get("remarks", "").strip()[:500]
#         document.updated_by = request.user
#         document.save(
#             update_fields=[
#                 "status",
#                 "remarks",
#                 "updated_by",
#                 "updated_at",
#             ]
#         )
#         refresh_joinee_status(document.joinee)

#     return redirect("onboarding:dashboard")


# @login_required
# @require_POST
# def add_document_type(request):
#     name = request.POST.get("name", "").strip()
#     category = request.POST.get("category", "other").strip()

#     valid_categories = {
#         value for value, label in DocumentType.CATEGORY_CHOICES
#     }

#     if name and category in valid_categories:
#         with transaction.atomic():
#             document_type, created = DocumentType.objects.get_or_create(
#                 name=name,
#                 defaults={"category": category, "is_active": True},
#             )

#             if not document_type.is_active:
#                 document_type.is_active = True
#                 document_type.category = category
#                 document_type.save(
#                     update_fields=["is_active", "category"]
#                 )

#             if created or document_type.is_active:
#                 for joinee in Joinee.objects.all():
#                     JoineeDocument.objects.get_or_create(
#                         joinee=joinee,
#                         document_type=document_type,
#                     )

#     return redirect("onboarding:dashboard")


# @login_required
# @require_POST
# def update_employee_code(request, joinee_id):
#     joinee = get_object_or_404(Joinee, pk=joinee_id)
#     employee_code = request.POST.get("employee_code", "").strip()

#     # An empty value is allowed so HR can correct a mistaken entry.
#     # Non-empty codes must be unique.
#     if employee_code:
#         duplicate = Joinee.objects.filter(
#             employee_code=employee_code
#         ).exclude(pk=joinee.pk).exists()

#         if duplicate:
#             return HttpResponse(
#                 "This Employee Code is already assigned to another joinee.",
#                 status=400,
#             )

#     joinee.employee_code = employee_code
#     joinee.save(update_fields=["employee_code", "updated_at"])
#     refresh_joinee_status(joinee)

#     return redirect("onboarding:dashboard")


# @login_required
# def export_excel(request):
#     seed_default_documents()

#     joinees = Joinee.objects.all().prefetch_related(
#         "documents__document_type"
#     )

#     for joinee in joinees:
#         ensure_joinee_documents(joinee)

#     workbook = Workbook()
#     summary = workbook.active
#     summary.title = "Pre-Joining Tracker"

#     summary_headers = [
#         "Onboarding Reference",
#         "Full Name",
#         "Personal Email",
#         "Phone",
#         "Designation",
#         "Department",
#         "Plant / Location",
#         "Joining Date",
#         "Employee Code",
#         "Overall Status",
#         "Created At",
#     ]
#     summary.append(summary_headers)

#     details = workbook.create_sheet("Document Statuses")
#     details.append([
#         "Onboarding Reference",
#         "Full Name",
#         "Employee Code",
#         "Document Category",
#         "Document Name",
#         "Document Status",
#         "Remarks",
#         "Last Updated",
#     ])

#     for joinee in joinees:
#         summary.append([
#             str(joinee.onboarding_reference),
#             joinee.full_name,
#             joinee.personal_email,
#             joinee.phone,
#             joinee.designation,
#             joinee.department,
#             joinee.plant_location,
#             joinee.joining_date.isoformat() if joinee.joining_date else "",
#             joinee.employee_code,
#             joinee.get_status_display(),
#             joinee.created_at.strftime("%Y-%m-%d %H:%M"),
#         ])

#         for doc in joinee.documents.all():
#             details.append([
#                 str(joinee.onboarding_reference),
#                 joinee.full_name,
#                 joinee.employee_code,
#                 doc.document_type.get_category_display(),
#                 doc.document_type.name,
#                 doc.get_status_display(),
#                 doc.remarks,
#                 doc.updated_at.strftime("%Y-%m-%d %H:%M"),
#             ])

#     for sheet in workbook.worksheets:
#         sheet.freeze_panes = "A2"
#         sheet.auto_filter.ref = sheet.dimensions

#         for cell in sheet[1]:
#             cell.font = Font(bold=True, color="FFFFFF")
#             cell.fill = PatternFill(
#                 fill_type="solid",
#                 fgColor="17365D",
#             )

#         for column_cells in sheet.columns:
#             max_length = max(
#                 len(str(cell.value or ""))
#                 for cell in column_cells
#             )
#             width = min(max(max_length + 2, 14), 38)
#             sheet.column_dimensions[
#                 get_column_letter(column_cells[0].column)
#             ].width = width

#     output = BytesIO()
#     workbook.save(output)
#     output.seek(0)

#     response = HttpResponse(
#         output.getvalue(),
#         content_type=(
#             "application/vnd.openxmlformats-officedocument."
#             "spreadsheetml.sheet"
#         ),
#     )
#     response["Content-Disposition"] = (
#         'attachment; filename="Vishakha_PreJoining_Tracker.xlsx"'
#     )
#     return response


from datetime import datetime
from io import BytesIO

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter

from .models import DocumentType, Joinee, JoineeDocument


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
