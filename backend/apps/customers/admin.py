from __future__ import annotations

from django.contrib import admin

from apps.customers.models import Customer


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ["name", "organization", "email", "company", "created_at"]
    list_filter = ["organization"]
    search_fields = ["name", "email", "company", "phone"]
    autocomplete_fields = ["organization"]
    readonly_fields = ["created_by", "created_at", "updated_at"]
