from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.invoices.models import Invoice, InvoiceStatus


class Command(BaseCommand):
    help = "Move 'sent' invoices past their due date to 'overdue'. Run from cron."

    def handle(self, *args: Any, **options: Any) -> None:
        today = timezone.now().date()
        due = Invoice.objects.filter(
            status=InvoiceStatus.SENT,
            due_date__isnull=False,
            due_date__lt=today,
        )
        count = 0
        for invoice in due:
            invoice.status = InvoiceStatus.OVERDUE
            invoice.save(update_fields=["status", "updated_at"])
            count += 1
        self.stdout.write(self.style.SUCCESS(f"Marked {count} invoice(s) overdue."))
