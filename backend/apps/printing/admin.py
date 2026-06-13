from django.contrib import admin
from django.contrib import messages
from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME
from django.template.response import TemplateResponse
from rest_framework.exceptions import ValidationError as DRFValidationError
from unfold.admin import ModelAdmin

from apps.printing.models import FilamentSpool, PrintBucket, PrintPrinter, PrintRequest
from apps.printing.serializers import PrintStartSerializer
from apps.printing import workflow
from config.admin_access import SuperuserOnlyModelAdmin


@admin.register(PrintBucket)
class PrintBucketAdmin(SuperuserOnlyModelAdmin, ModelAdmin):
    list_display = ("name", "makerspace", "is_active", "updated_at")
    list_filter = ("is_active", "makerspace")
    search_fields = ("name", "description", "makerspace__name", "makerspace__slug")
    readonly_fields = ("created_at", "updated_at")
    fields = (
        "makerspace",
        "name",
        "description",
        "is_active",
        "created_at",
        "updated_at",
    )


@admin.register(PrintRequest)
class PrintRequestAdmin(SuperuserOnlyModelAdmin, ModelAdmin):
    actions = [
        "accept_selected",
        "reject_selected",
        "complete_selected",
        "fail_selected",
        "start_selected",
    ]
    list_display = ("status", "bucket", "printer", "requester", "created_at")
    list_filter = ("status", "bucket__makerspace", "bucket", "printer")
    search_fields = (
        "title",
        "description",
        "requester__username",
        "requester__email",
        "bucket__name",
    )
    readonly_fields = (
        "status",
        "reason",
        "handled_by",
        "printer",
        "filament_spool",
        "estimated_minutes",
        "estimated_filament_grams",
        "created_at",
        "accepted_at",
        "started_at",
        "completed_at",
        "updated_at",
    )
    fields = (
        "bucket",
        "requester",
        "title",
        "description",
        "material",
        "color",
        "quantity",
        "source_link",
        "model_file",
        "preferred_settings",
        "estimate_screenshot",
        "preview_screenshot",
        "status",
        "reason",
        "handled_by",
        "printer",
        "filament_spool",
        "estimated_minutes",
        "estimated_filament_grams",
        "created_at",
        "accepted_at",
        "started_at",
        "completed_at",
        "updated_at",
    )

    @admin.action(description="Accept selected print requests")
    def accept_selected(self, request, queryset):
        success_count = 0
        for print_request in queryset:
            try:
                workflow.accept(print_request, request.user)
            except workflow.InvalidTransition as exc:
                self.message_user(
                    request,
                    f"{print_request.pk}: {exc}",
                    level=messages.ERROR,
                )
            else:
                success_count += 1

        if success_count:
            self.message_user(
                request,
                f"Accepted {success_count} print request(s).",
                level=messages.SUCCESS,
            )

    @admin.action(description="Reject selected print requests (with reason)")
    def reject_selected(self, request, queryset):
        if "apply" not in request.POST:
            return self._intermediate_action_response(
                request,
                queryset,
                "admin/printing/reject_action.html",
                "Reject selected print requests",
                "reject_selected",
            )

        reason = request.POST.get("reason", "").strip()
        if not reason:
            self.message_user(
                request,
                "Rejection reason is required.",
                level=messages.ERROR,
            )
            return None

        success_count = 0
        for print_request in queryset:
            try:
                workflow.reject(print_request, request.user, reason)
            except workflow.InvalidTransition as exc:
                self.message_user(
                    request,
                    f"{print_request.pk}: {exc}",
                    level=messages.ERROR,
                )
            else:
                success_count += 1

        if success_count:
            self.message_user(
                request,
                f"Rejected {success_count} print request(s).",
                level=messages.SUCCESS,
            )
        return None

    @admin.action(description="Complete selected print requests")
    def complete_selected(self, request, queryset):
        success_count = 0
        for print_request in queryset:
            try:
                workflow.complete(print_request, request.user)
            except workflow.InvalidTransition as exc:
                self.message_user(
                    request,
                    f"{print_request.pk}: {exc}",
                    level=messages.ERROR,
                )
            else:
                success_count += 1

        if success_count:
            self.message_user(
                request,
                f"Completed {success_count} print request(s).",
                level=messages.SUCCESS,
            )

    @admin.action(description="Fail selected print requests (with reason)")
    def fail_selected(self, request, queryset):
        if "apply" not in request.POST:
            return self._intermediate_action_response(
                request,
                queryset,
                "admin/printing/fail_action.html",
                "Fail selected print requests",
                "fail_selected",
            )

        reason = request.POST.get("reason", "").strip()
        if not reason:
            self.message_user(
                request,
                "Failure reason is required.",
                level=messages.ERROR,
            )
            return None

        success_count = 0
        for print_request in queryset:
            try:
                workflow.fail(print_request, request.user, reason)
            except workflow.InvalidTransition as exc:
                self.message_user(
                    request,
                    f"{print_request.pk}: {exc}",
                    level=messages.ERROR,
                )
            else:
                success_count += 1

        if success_count:
            self.message_user(
                request,
                f"Failed {success_count} print request(s).",
                level=messages.SUCCESS,
            )
        return None

    @admin.action(description="Start selected print requests (assign printer/spool)")
    def start_selected(self, request, queryset):
        if "apply" not in request.POST:
            return self._intermediate_action_response(
                request,
                queryset,
                "admin/printing/start_action.html",
                "Start selected print requests",
                "start_selected",
            )

        success_count = 0
        for print_request in queryset:
            # Validate the per-request inputs through the same serializer the API uses
            # (handles the decimal filament field + min_value bounds), then start.
            raw = {
                "printer_id": request.POST.get(f"printer_id_{print_request.pk}", ""),
                "filament_spool_id": request.POST.get(
                    f"filament_spool_id_{print_request.pk}", ""
                ),
                "estimated_minutes": request.POST.get(
                    f"estimated_minutes_{print_request.pk}", ""
                ),
                "estimated_filament_grams": request.POST.get(
                    f"estimated_filament_grams_{print_request.pk}", ""
                ),
            }
            payload = {key: value for key, value in raw.items() if str(value).strip()}
            serializer = PrintStartSerializer(data=payload)
            if not serializer.is_valid():
                self.message_user(
                    request,
                    f"{print_request.pk}: {serializer.errors}",
                    level=messages.ERROR,
                )
                continue
            try:
                workflow.start(print_request, request.user, **serializer.validated_data)
            except (DRFValidationError, workflow.InvalidTransition) as exc:
                self.message_user(
                    request,
                    f"{print_request.pk}: {exc}",
                    level=messages.ERROR,
                )
            else:
                success_count += 1

        if success_count:
            self.message_user(
                request,
                f"Started {success_count} print request(s).",
                level=messages.SUCCESS,
            )
        return None

    def _intermediate_action_response(
        self,
        request,
        queryset,
        template_name,
        title,
        action_name,
    ):
        context = {
            **self.admin_site.each_context(request),
            "title": title,
            "queryset": queryset,
            "opts": self.model._meta,
            "action_name": action_name,
            "action_checkbox_name": ACTION_CHECKBOX_NAME,
        }
        return TemplateResponse(request, template_name, context)


@admin.register(PrintPrinter)
class PrintPrinterAdmin(SuperuserOnlyModelAdmin, ModelAdmin):
    list_display = ("name", "makerspace", "status", "is_active", "updated_at")
    list_filter = ("status", "is_active", "makerspace")
    search_fields = ("name", "model", "notes", "makerspace__name", "makerspace__slug")
    readonly_fields = ("created_at", "updated_at")
    fields = (
        "makerspace",
        "name",
        "model",
        "status",
        "notes",
        "is_active",
        "created_at",
        "updated_at",
    )


@admin.register(FilamentSpool)
class FilamentSpoolAdmin(SuperuserOnlyModelAdmin, ModelAdmin):
    list_display = (
        "material",
        "color",
        "printer",
        "makerspace",
        "remaining_weight_grams",
        "is_active",
    )
    list_filter = ("material", "is_active", "makerspace", "printer")
    search_fields = (
        "material",
        "color",
        "brand",
        "lot_code",
        "printer__name",
        "makerspace__name",
    )
    readonly_fields = ("created_at", "updated_at")
    fields = (
        "makerspace",
        "printer",
        "material",
        "color",
        "brand",
        "lot_code",
        "initial_weight_grams",
        "remaining_weight_grams",
        "is_active",
        "opened_at",
        "created_at",
        "updated_at",
    )
