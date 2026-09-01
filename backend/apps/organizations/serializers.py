from __future__ import annotations

from rest_framework import serializers

from apps.accounts.serializers import UserSerializer
from apps.organizations.models import Membership, Organization, Role
from apps.organizations.selectors import membership_for

ASSIGNABLE_ROLE_CHOICES = [
    (Role.ADMIN, Role.ADMIN.label),
    (Role.MEMBER, Role.MEMBER.label),
]

NAME_MIN_LENGTH = 2
NAME_MAX_LENGTH = 120


class OrganizationSerializer(serializers.ModelSerializer):
    """Serializer for the organizations endpoint.

    ``name`` is the only writable field. ``role`` is the *requesting* user's
    role in this organization and is always read-only - role changes are not
    part of this endpoint.
    """

    role = serializers.SerializerMethodField()

    class Meta:
        model = Organization
        fields = ["id", "name", "role", "created_at", "updated_at"]
        read_only_fields = ["id", "role", "created_at", "updated_at"]

    def get_role(self, obj: Organization) -> str | None:
        # Fast path: annotated by the viewset's queryset.
        annotated = getattr(obj, "current_user_role", None)
        if annotated is not None:
            return annotated
        request = self.context.get("request")
        if request is None or not request.user.is_authenticated:
            return None
        membership = membership_for(request.user, obj)
        return membership.role if membership else None

    def validate_name(self, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) < NAME_MIN_LENGTH:
            raise serializers.ValidationError(
                f"Organization name must be at least {NAME_MIN_LENGTH} characters."
            )
        if len(cleaned) > NAME_MAX_LENGTH:
            raise serializers.ValidationError(
                f"Organization name must be at most {NAME_MAX_LENGTH} characters."
            )
        return cleaned


class MembershipSerializer(serializers.ModelSerializer):
    """Read representation of a member: the user plus their role."""

    user = UserSerializer(read_only=True)

    class Meta:
        model = Membership
        fields = ["user", "role", "created_at", "updated_at"]
        read_only_fields = fields


class AddMemberSerializer(serializers.Serializer):
    """Payload for ``POST .../members/`` - adds an existing user by email."""

    email = serializers.EmailField()
    role = serializers.ChoiceField(choices=ASSIGNABLE_ROLE_CHOICES)


class ChangeMemberRoleSerializer(serializers.Serializer):
    """Payload for ``PATCH .../members/{user_id}/``."""

    role = serializers.ChoiceField(choices=ASSIGNABLE_ROLE_CHOICES)
