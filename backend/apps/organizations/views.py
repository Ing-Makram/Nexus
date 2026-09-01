from __future__ import annotations

from django.db.models import OuterRef, QuerySet, Subquery
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.organizations.models import Membership, Organization
from apps.organizations.permissions import (
    CanManageOrganizationMembers,
    IsOrganizationAdmin,
    IsOrganizationMember,
    IsOrganizationMemberForRoute,
    IsOrganizationOwner,
)
from apps.organizations.selectors import members_of, organizations_for_user
from apps.organizations.serializers import (
    AddMemberSerializer,
    ChangeMemberRoleSerializer,
    MembershipSerializer,
    OrganizationSerializer,
)
from apps.organizations.services import (
    add_member,
    change_member_role,
    create_organization,
    remove_member,
)


class OrganizationViewSet(viewsets.ModelViewSet):
    """CRUD for organizations, strictly scoped to the requesting user.

    Tenant isolation is enforced twice:
      1. ``get_queryset`` only ever returns the user's own organizations, so a
         non-member receives 404 (existence is never revealed).
      2. Per-action object permissions add role checks on top.
    """

    serializer_class = OrganizationSerializer

    _permissions_by_action: dict[str, list[type[BasePermission]]] = {
        "retrieve": [IsAuthenticated, IsOrganizationMember],
        "update": [IsAuthenticated, IsOrganizationAdmin],
        "partial_update": [IsAuthenticated, IsOrganizationAdmin],
        "destroy": [IsAuthenticated, IsOrganizationOwner],
    }

    def get_permissions(self) -> list[BasePermission]:
        classes = self._permissions_by_action.get(self.action, [IsAuthenticated])
        return [cls() for cls in classes]

    def get_queryset(self) -> QuerySet[Organization]:
        user = self.request.user
        role_subquery = Membership.objects.filter(organization=OuterRef("pk"), user=user).values(
            "role"
        )[:1]
        return (
            organizations_for_user(user)
            .distinct()
            .annotate(current_user_role=Subquery(role_subquery))
            .order_by("name")
        )

    def perform_create(self, serializer: OrganizationSerializer) -> None:
        serializer.instance = create_organization(
            name=serializer.validated_data["name"],
            user=self.request.user,
        )


class MembershipViewSet(viewsets.ViewSet):
    """Members of a single organization, nested under
    ``/organizations/{organization_id}/members/``.

    Tenant isolation: ``get_organization()`` is scoped to the caller's
    organizations, so any request for an organization the caller does not belong
    to returns 404 before permissions or business rules run.
    """

    def get_permissions(self) -> list[BasePermission]:
        if self.action == "list":
            return [IsAuthenticated(), IsOrganizationMemberForRoute()]
        return [IsAuthenticated(), CanManageOrganizationMembers()]

    def get_organization(self) -> Organization:
        if not hasattr(self, "_organization"):
            self._organization = get_object_or_404(
                organizations_for_user(self.request.user).distinct(),
                pk=self.kwargs["organization_id"],
            )
        return self._organization

    def list(self, request: Request, organization_id: int) -> Response:
        organization = self.get_organization()
        serializer = MembershipSerializer(members_of(organization), many=True)
        return Response(serializer.data)

    def create(self, request: Request, organization_id: int) -> Response:
        organization = self.get_organization()
        payload = AddMemberSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        membership = add_member(
            organization=organization,
            actor=request.user,
            email=payload.validated_data["email"],
            role=payload.validated_data["role"],
        )
        return Response(MembershipSerializer(membership).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request: Request, organization_id: int, user_id: int) -> Response:
        organization = self.get_organization()
        payload = ChangeMemberRoleSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        membership = change_member_role(
            organization=organization,
            actor=request.user,
            target_user_id=user_id,
            role=payload.validated_data["role"],
        )
        return Response(MembershipSerializer(membership).data)

    def destroy(self, request: Request, organization_id: int, user_id: int) -> Response:
        organization = self.get_organization()
        remove_member(
            organization=organization,
            actor=request.user,
            target_user_id=user_id,
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
