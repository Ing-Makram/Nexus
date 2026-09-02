from django.urls import path

from apps.dashboard.views import DashboardTimeseriesView, DashboardView

app_name = "dashboard"

urlpatterns = [
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path(
        "dashboard/timeseries/",
        DashboardTimeseriesView.as_view(),
        name="dashboard-timeseries",
    ),
]
