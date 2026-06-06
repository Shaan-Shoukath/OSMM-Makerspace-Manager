from django.contrib import admin
from unfold.admin import ModelAdmin

from apps.makerspaces.models import Makerspace


@admin.register(Makerspace)
class MakerspaceAdmin(ModelAdmin):
    list_display = (
        "name",
        "slug",
        "location",
        "public_inventory_enabled",
        "updated_at",
    )
    list_filter = ("public_inventory_enabled",)
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "slug", "location")
