from __future__ import annotations

from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.dashboard.selectors import (
    TIMESERIES_RANGES,
    dashboard_stats,
    dashboard_timeseries,
)
from apps.organizations.models import Organization
from apps.organizations.selectors import organizations_for_user


def _resolve_organization(request: Request) -> tuple[Organization | None, Response | None]:
    """Read ``?organization=<id>`` and scope it to the caller.

    Returns ``(organization, None)`` on success, or ``(None, error_response)``
    with a 400 (missing/invalid param) or 404 (not one of the caller's orgs, so
    the existence of other tenants is never revealed).
    """
    raw = request.query_params.get("organization")
    if not raw or not raw.isdigit():
        return None, Response(
            {"organization": "This query parameter is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    organization = organizations_for_user(request.user).filter(pk=int(raw)).first()
    if organization is None:
        return None, Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

    return organization, None


class DashboardView(APIView):
    """``GET /api/v1/dashboard/?organization=<id>`` - aggregate figures for one
    organization.

    Any member of the organization may read it (no role gate - it exposes only
    aggregates the member can already compute from the list endpoints). Tenant
    isolation: the organization must be one the caller belongs to, otherwise 404.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        organization, error = _resolve_organization(request)
        if error is not None:
            return error

        return Response(dashboard_stats(user=request.user, organization=organization))


class DashboardTimeseriesView(APIView):
    """``GET /api/v1/dashboard/timeseries/?organization=<id>&days=<30|90>`` -
    daily order / invoice / customer counts and invoiced / paid amounts.

    Same tenant rules as :class:`DashboardView`. ``days`` defaults to 30 and must
    be one of the supported windows, otherwise 400.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        organization, error = _resolve_organization(request)
        if error is not None:
            return error

        raw_days = request.query_params.get("days", "30")
        if not raw_days.isdigit() or int(raw_days) not in TIMESERIES_RANGES:
            return Response(
                {"days": f"Must be one of {sorted(TIMESERIES_RANGES)}."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            dashboard_timeseries(user=request.user, organization=organization, days=int(raw_days))
        )
