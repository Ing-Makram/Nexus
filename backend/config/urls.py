from django.contrib import admin
from django.urls import include, path
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from config.health import liveness, readiness


class HealthCheckView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"status": "ok", "message": "NEXUS Backend is running"})


urlpatterns = [
    path("admin/", admin.site.urls),
    # Orchestration probes (see config/health.py).
    path("health/", liveness, name="health-liveness"),
    path("health/ready/", readiness, name="health-readiness"),
    # Existing application health endpoint (kept for backwards compatibility).
    path("api/health/", HealthCheckView.as_view(), name="health-check"),
    path("api/v1/auth/", include("apps.accounts.urls")),
    path("api/v1/", include("apps.dashboard.urls")),
    path("api/v1/", include("apps.organizations.urls")),
    path("api/v1/", include("apps.customers.urls")),
    path("api/v1/", include("apps.orders.urls")),
    path("api/v1/", include("apps.invoices.urls")),
]
