from django.urls import path

from . import views

app_name = "onboarding"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("add/", views.add_joinee, name="add_joinee"),
    path(
        "document/<int:document_id>/update/",
        views.update_document,
        name="update_document",
    ),
    path(
        "documents/add-type/",
        views.add_document_type,
        name="add_document_type",
    ),
    path(
        "joinee/<int:joinee_id>/employee-code/",
        views.update_employee_code,
        name="update_employee_code",
    ),
    path(
        "joinee/<int:joinee_id>/",
        views.joinee_detail,
        name="joinee_detail",
    ),
    path("export/", views.export_excel, name="export_excel"),

    path(
    "joinee/<int:joinee_id>/joining-kit/create/",
    views.create_joining_kit_request,
    name="create_joining_kit_request",
    ),
    path(
        "joining-kit/<int:request_id>/",
        views.joining_kit_detail,
        name="joining_kit_detail",
    ),

    path(
    "joining-kit/manager/",
    views.manager_joining_kit_dashboard,
    name="manager_joining_kit_dashboard",
    ),
    path(
        "joining-kit/<int:request_id>/",
        views.joining_kit_detail,
        name="joining_kit_detail",
    ),
    path(
    "joining-kit/manager/",
    views.manager_joining_kit_dashboard,
    name="manager_joining_kit_dashboard",
    ),
    path(
        "joining-kit/<int:request_id>/",
        views.joining_kit_detail,
        name="joining_kit_detail",
    ),
]
