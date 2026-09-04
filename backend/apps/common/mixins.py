from __future__ import annotations

from rest_framework.permissions import BasePermission, IsAuthenticated


class PermissionsByActionMixin:
    """Resolve ``get_permissions()`` from the subclass's ``_permissions_by_action``
    mapping (``{action: [PermissionClass, ...]}``), defaulting to
    ``[IsAuthenticated]`` for any action not listed there.

    Each ViewSet keeps its own ``_permissions_by_action``; this mixin only
    implements the shared dispatch.
    """

    _permissions_by_action: dict[str, list[type[BasePermission]]] = {}

    def get_permissions(self) -> list[BasePermission]:
        classes = self._permissions_by_action.get(self.action, [IsAuthenticated])
        return [cls() for cls in classes]
