import segno
from django.contrib import admin
from django.utils.safestring import mark_safe
from unfold.admin import ModelAdmin

from apps.boxes.models import Box, QrCode, QrScanEvent
from config.admin_access import SuperuserOnlyModelAdmin


@admin.register(Box)
class BoxAdmin(SuperuserOnlyModelAdmin, ModelAdmin):
    list_display = ("label", "makerspace", "parent", "code", "is_active", "updated_at")
    list_filter = ("makerspace", "is_active")
    search_fields = ("label", "code", "location")
    autocomplete_fields = ("makerspace", "parent")
    readonly_fields = ("code", "qr_preview", "created_at", "updated_at")

    def qr_preview(self, obj):
        if not obj or not obj.pk:
            return "(save first to generate the QR)"
        return mark_safe(segno.make(obj.code).svg_inline(scale=4))

    qr_preview.short_description = "QR tag"


@admin.register(QrCode)
class QrCodeAdmin(SuperuserOnlyModelAdmin, ModelAdmin):
    list_display = ("payload", "makerspace", "target_type", "target_id", "status", "updated_at")
    list_filter = ("makerspace", "target_type", "status")
    search_fields = ("payload",)
    readonly_fields = ("payload", "created_at", "updated_at", "revoked_at")


@admin.register(QrScanEvent)
class QrScanEventAdmin(SuperuserOnlyModelAdmin, ModelAdmin):
    list_display = ("qr_code", "makerspace", "context", "actor", "created_at")
    list_filter = ("makerspace", "context")
    search_fields = ("qr_code__payload",)
    readonly_fields = ("qr_code", "makerspace", "request", "actor", "context", "created_at")
