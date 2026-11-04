"""URLs raíz de SG-Prod."""

from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="personal:login", permanent=False)),
    path("admin/", admin.site.urls),
    path("personal/", include("apps.personal.urls")),
    path("dashboard/", include("apps.dashboard.urls")),
    path("api/", include("apps.api.urls")),
]
