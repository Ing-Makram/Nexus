from __future__ import annotations

from django.db.models import QuerySet
from rest_framework import viewsets
from rest_framework.permissions import BasePermission, IsAuthenticated

from apps.common.query_params import parse_date_param
from apps.orders.models import Order, OrderStatus
from apps.orders.permissions import CanManageOrders, CanReadOrders
from apps.orders.selectors import orders_for_user
from apps.orders.serializers import OrderSerializer
from apps.orders.services import WRITABLE_FIELDS, create_order, delete_order, update_order


class OrderViewSet(viewsets.ModelViewSet):
    """CRUD for orders, strictly scoped to the caller's organizations.

    Tenant isolation: ``get_queryset`` only ever returns orders from
    organizations the caller belongs to, so any cross-tenant request resolves
    to 404. Per-action permissions add the role checks - any member may read,
    owners and admins may create, update and delete. All writes go through the
    service layer (``perform_*`` never touches the ORM directly).
    """

    serializer_class = OrderSerializer

    _permissions_by_action: dict[str, list[type[BasePermission]]] = {
        "create": [IsAuthenticated, CanManageOrders],
        "retrieve": [IsAuthenticated, CanReadOrders],
        "update": [IsAuthenticated, CanManageOrders],
        "partial_update": [IsAuthenticated, CanManageOrders],
        "destroy": [IsAuthenticated, CanManageOrders],
    }

    def get_permissions(self) -> list[BasePermission]:
        classes = self._permissions_by_action.get(self.action, [IsAuthenticated])
        return [cls() for cls in classes]

    def get_queryset(self) -> QuerySet[Order]:
        queryset = orders_for_user(self.request.user)
        organization = self.request.query_params.get("organization")
        if organization and organization.isdigit():
            queryset = queryset.filter(organization_id=organization)
        status = self.request.query_params.get("status")
        if status:
            queryset = queryset.filter(status=status)
        date_from = parse_date_param(self.request.query_params.get("date_from"))
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        date_to = parse_date_param(self.request.query_params.get("date_to"))
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)
        return queryset

    def perform_create(self, serializer: OrderSerializer) -> None:
        data = serializer.validated_data
        serializer.instance = create_order(
            organization=data["organization"],
            actor=self.request.user,
            customer=data["customer"],
            total_amount=data["total_amount"],
            status=data.get("status", OrderStatus.DRAFT),
            notes=data.get("notes", ""),
        )

    def perform_update(self, serializer: OrderSerializer) -> None:
        fields = {
            key: value for key, value in serializer.validated_data.items() if key in WRITABLE_FIELDS
        }
        serializer.instance = update_order(
            order=serializer.instance, actor=self.request.user, **fields
        )

    def perform_destroy(self, instance: Order) -> None:
        delete_order(order=instance, actor=self.request.user)
