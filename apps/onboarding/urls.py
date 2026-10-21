# from django.urls import path

# from . import views

# app_name = "onboarding"

# urlpatterns = [
#     path("", views.dashboard, name="dashboard"),
#     path("add/", views.add_joinee, name="add_joinee"),
#     path(
#         "document/<int:document_id>/update/",
#         views.update_document,
#         name="update_document",
#     ),
#     path(
#         "documents/add-type/",
#         views.add_document_type,
#         name="add_document_type",
#     ),
#     path(
#         "joinee/<int:joinee_id>/employee-code/",
#         views.update_employee_code,
#         name="update_employee_code",
#     ),
#     path("export/", views.export_excel, name="export_excel"),

#     path(
#     "<int:joinee_id>/",
#     views.joinee_detail,
#     name="joinee_detail",
# ),
# ]




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
]
