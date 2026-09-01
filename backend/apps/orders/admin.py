from __future__ import annotations

from django.contrib import admin

from apps.orders.models import Order


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ["id", "organization", "customer", "status", "total_amount", "created_at"]
    list_filter = ["status", "organization"]
    search_fields = ["customer__name", "notes"]
    autocomplete_fields = ["organization", "customer"]
    readonly_fields = ["created_by", "created_at", "updated_at"]
    ordering = ["-created_at"]
