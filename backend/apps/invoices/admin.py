from __future__ import annotations

from django.contrib import admin

from apps.invoices.models import Invoice


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = [
        "invoice_number",
        "organization",
        "customer",
        "status",
        "total_amount",
        "issue_date",
        "due_date",
    ]
    list_filter = ["status", "organization"]
    search_fields = ["invoice_number", "customer__name", "notes"]
    autocomplete_fields = ["organization", "customer", "order"]
    readonly_fields = ["created_by", "created_at", "updated_at"]
    ordering = ["-created_at"]
