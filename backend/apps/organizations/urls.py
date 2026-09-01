from django.urls import path
from rest_framework.routers import SimpleRouter

from apps.organizations.views import MembershipViewSet, OrganizationViewSet

app_name = "organizations"

router = SimpleRouter()
router.register(r"organizations", OrganizationViewSet, basename="organization")

_member_collection = MembershipViewSet.as_view({"get": "list", "post": "create"})
_member_item = MembershipViewSet.as_view({"patch": "partial_update", "delete": "destroy"})

urlpatterns = [
    *router.urls,
    path(
        "organizations/<int:organization_id>/members/",
        _member_collection,
        name="member-list",
    ),
    path(
        "organizations/<int:organization_id>/members/<int:user_id>/",
        _member_item,
        name="member-detail",
    ),
]
