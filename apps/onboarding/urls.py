from django.urls import path
from . import views

app_name = "onboarding"

urlpatterns = [
    # HR asset request dashboard
    path("", views.dashboard, name="dashboard"),
    path("add/", views.add_joinee, name="add_joinee"),
    path("export/", views.export_excel, name="export_excel"),

    # Employee record utilities
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

    # HR creates the asset request; manager selects assets
    path(
        "joinee/<int:joinee_id>/joining-kit/create/",
        views.create_joining_kit_request,
        name="create_joining_kit_request",
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