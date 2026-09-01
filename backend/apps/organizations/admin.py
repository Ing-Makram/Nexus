from __future__ import annotations

from django.contrib import admin

from apps.organizations.models import Membership, Organization


class MembershipInline(admin.TabularInline):
    model = Membership
    extra = 0
    autocomplete_fields = ["user"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ["name", "created_by", "created_at", "updated_at"]
    search_fields = ["name"]
    readonly_fields = ["created_at", "updated_at"]
    inlines = [MembershipInline]


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ["organization", "user", "role", "created_at"]
    list_filter = ["role"]
    search_fields = ["organization__name", "user__email"]
    autocomplete_fields = ["organization", "user"]
    readonly_fields = ["created_at", "updated_at"]
