from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.dashboard.selectors import dashboard_stats
from apps.organizations.selectors import organizations_for_user


class DashboardView(APIView):
    """``GET /api/v1/dashboard/?organization=<id>`` - aggregate figures for one
    organization.

    Any member of the organization may read it (no role gate - it exposes only
    aggregates the member can already compute from the list endpoints). Tenant
    isolation: the organization must be one the caller belongs to, otherwise 404.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        raw = request.query_params.get("organization")
        if not raw or not raw.isdigit():
            return Response(
                {"organization": "This query parameter is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        organization = organizations_for_user(request.user).filter(pk=int(raw)).first()
        if organization is None:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        return Response(dashboard_stats(user=request.user, organization=organization))
