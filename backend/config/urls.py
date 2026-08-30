from django.urls import path
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthCheckView(APIView):
    def get(self, request):
        return Response({"status": "ok", "message": "NEXUS Backend is running"})


urlpatterns = [
    path("api/health/", HealthCheckView.as_view(), name="health-check"),
]
