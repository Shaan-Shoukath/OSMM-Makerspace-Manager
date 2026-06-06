from django.contrib import admin
from unfold.admin import ModelAdmin

from apps.inventory.models import InventoryProduct


@admin.register(InventoryProduct)
class InventoryProductAdmin(ModelAdmin):
    list_display = (
        "name",
        "makerspace",
        "is_public",
        "public_availability_mode",
        "available_quantity",
        "total_quantity",
        "is_archived",
        "updated_at",
    )
    list_filter = (
        "makerspace",
        "is_public",
        "is_archived",
        "public_availability_mode",
    )
    search_fields = ("name", "description", "makerspace__name", "makerspace__slug")
    list_select_related = ("makerspace",)
