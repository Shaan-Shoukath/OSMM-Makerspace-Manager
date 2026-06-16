from decimal import Decimal

from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone

from apps.audit import services as audit
from apps.printing.emails import send_print_email
from apps.printing.models import FilamentSpool, PrintPrinter, PrintRequest


class InvalidTransition(Exception):
    pass


_ALLOWED = {
    PrintRequest.Status.PENDING: {
        PrintRequest.Status.ACCEPTED,
        PrintRequest.Status.REJECTED,
    },
    PrintRequest.Status.ACCEPTED: {PrintRequest.Status.PRINTING},
    PrintRequest.Status.PRINTING: {
        PrintRequest.Status.COMPLETED,
        PrintRequest.Status.FAILED,
    },
}


def _transition(
    print_request,
    actor,
    status,
    event,
    reason="",
    printer_id=None,
    filament_spool_id=None,
    estimated_minutes=None,
    estimated_filament_grams=None,
    percent_complete=0,
):
    with transaction.atomic():
        locked = (
            PrintRequest.objects.select_for_update()
            .select_related("bucket__makerspace", "requester")
            .get(pk=print_request.pk)
        )
        if status not in _ALLOWED.get(locked.status, set()):
            raise InvalidTransition(
                f"Cannot transition print request from {locked.status} to {status}."
            )

        extra_update_fields = []
        if status == PrintRequest.Status.PRINTING:
            _assign_print_job(
                locked,
                printer_id=printer_id,
                filament_spool_id=filament_spool_id,
                estimated_minutes=estimated_minutes,
                estimated_filament_grams=estimated_filament_grams,
            )
            locked.started_at = timezone.now()
            extra_update_fields.extend(
                [
                    "printer",
                    "filament_spool",
                    "estimated_minutes",
                    "estimated_filament_grams",
                    "started_at",
                ]
            )

        locked.status = status
        locked.handled_by = actor
        if status == PrintRequest.Status.ACCEPTED:
            locked.accepted_at = timezone.now()
        if status == PrintRequest.Status.COMPLETED:
            locked.completed_at = timezone.now()
        if status in (PrintRequest.Status.REJECTED, PrintRequest.Status.FAILED):
            locked.reason = reason

        locked.save(
            update_fields=[
                "status",
                "handled_by",
                "accepted_at",
                "started_at",
                "completed_at",
                "reason",
                "updated_at",
            ]
            + extra_update_fields
        )
        audit.record(
            actor,
            f"print.{event}",
            makerspace=locked.bucket.makerspace,
            target=locked,
        )
        if (
            status == PrintRequest.Status.COMPLETED
            and locked.filament_spool_id
            and locked.estimated_filament_grams
            and locked.estimated_filament_grams > 0
        ):
            _deduct_spool(
                actor,
                locked,
                locked.estimated_filament_grams,
                reason="completed",
            )
        elif (
            status == PrintRequest.Status.FAILED
            and locked.filament_spool_id
            and locked.estimated_filament_grams
            and locked.estimated_filament_grams > 0
            and percent_complete
            and percent_complete > 0
        ):
            partial = (
                locked.estimated_filament_grams
                * Decimal(percent_complete)
                / Decimal(100)
            ).quantize(Decimal("0.01"))
            if partial > 0:
                _deduct_spool(actor, locked, partial, reason="failed_partial")
        if event in {"accepted", "started", "rejected", "completed"}:
            transaction.on_commit(
                lambda request_id=locked.pk, email_event=event: send_print_email(
                    email_event,
                    PrintRequest.objects.select_related(
                        "bucket__makerspace", "requester"
                    ).get(pk=request_id),
                )
            )
        return locked


def _deduct_spool(actor, locked, grams, *, reason):
    spool = FilamentSpool.objects.select_for_update().get(pk=locked.filament_spool_id)
    remaining_before = spool.remaining_weight_grams
    spool.remaining_weight_grams = max(remaining_before - grams, Decimal("0"))
    spool.save(update_fields=["remaining_weight_grams", "updated_at"])
    locked.filament_grams_used = grams
    locked.save(update_fields=["filament_grams_used"])
    audit.record(
        actor,
        "print.spool_deducted",
        makerspace=locked.bucket.makerspace,
        target=spool,
        meta={
            "spool_id": spool.id,
            "deducted_grams": str(grams),
            "remaining_before": str(remaining_before),
            "remaining_after": str(spool.remaining_weight_grams),
            "print_request_id": locked.id,
            "reason": reason,
        },
    )


def _assign_print_job(
    print_request,
    *,
    printer_id,
    filament_spool_id,
    estimated_minutes,
    estimated_filament_grams,
):
    if printer_id is not None:
        try:
            printer = PrintPrinter.objects.select_for_update().get(pk=printer_id)
        except ObjectDoesNotExist as exc:
            raise InvalidTransition("Printer was not found.") from exc
        if printer.makerspace_id != print_request.bucket.makerspace_id:
            raise InvalidTransition("Printer must belong to the request makerspace.")
        if not printer.is_active or printer.status != PrintPrinter.Status.ACTIVE:
            raise InvalidTransition("Printer is not available for printing.")
        if printer.print_requests.filter(status=PrintRequest.Status.PRINTING).exists():
            raise InvalidTransition("Printer already has an active print job.")
        print_request.printer = printer

    if filament_spool_id is not None:
        try:
            spool = FilamentSpool.objects.select_for_update().get(pk=filament_spool_id)
        except ObjectDoesNotExist as exc:
            raise InvalidTransition("Filament spool was not found.") from exc
        if spool.makerspace_id != print_request.bucket.makerspace_id:
            raise InvalidTransition("Filament spool must belong to the request makerspace.")
        if print_request.printer_id and spool.printer_id not in (None, print_request.printer_id):
            raise InvalidTransition("Filament spool is assigned to a different printer.")
        if not spool.is_active:
            raise InvalidTransition("Filament spool is not active.")
        print_request.filament_spool = spool

    if estimated_minutes is not None:
        print_request.estimated_minutes = estimated_minutes
    if estimated_filament_grams is not None:
        print_request.estimated_filament_grams = estimated_filament_grams

    if (
        print_request.filament_spool_id
        and print_request.estimated_filament_grams
        and print_request.estimated_filament_grams
        > print_request.filament_spool.remaining_weight_grams
    ):
        raise InvalidTransition("Estimated filament exceeds remaining spool weight.")


def accept(print_request, actor):
    return _transition(
        print_request,
        actor,
        PrintRequest.Status.ACCEPTED,
        "accepted",
    )


def reject(print_request, actor, reason):
    return _transition(
        print_request,
        actor,
        PrintRequest.Status.REJECTED,
        "rejected",
        reason=reason,
    )


def start(
    print_request,
    actor,
    *,
    printer_id=None,
    filament_spool_id=None,
    estimated_minutes=None,
    estimated_filament_grams=None,
):
    return _transition(
        print_request,
        actor,
        PrintRequest.Status.PRINTING,
        "started",
        printer_id=printer_id,
        filament_spool_id=filament_spool_id,
        estimated_minutes=estimated_minutes,
        estimated_filament_grams=estimated_filament_grams,
    )


def complete(print_request, actor):
    return _transition(
        print_request,
        actor,
        PrintRequest.Status.COMPLETED,
        "completed",
    )


def fail(print_request, actor, reason, percent_complete=0):
    return _transition(
        print_request,
        actor,
        PrintRequest.Status.FAILED,
        "failed",
        reason=reason,
        percent_complete=percent_complete,
    )


def reprint(failed_request, actor):
    with transaction.atomic():
        locked = (
            PrintRequest.objects.select_for_update()
            .select_related("bucket__makerspace")
            .get(pk=failed_request.pk)
        )
        if locked.status != PrintRequest.Status.FAILED:
            raise InvalidTransition("Only failed print requests can be reprinted.")
        # Anchor every reprint to the file-owning original root, not the immediate
        # failed attempt. Reprint clones never own PrintRequestFile rows, so pointing a
        # reprint-of-a-reprint at its parent (which also has no files) would lose the
        # model files. The root original holds the files, so the serializer's one-hop
        # file fallback stays correct no matter how many retries occur.
        root = locked.reprint_of if locked.reprint_of_id else locked
        clone = PrintRequest.objects.create(
            bucket=locked.bucket,
            requester=locked.requester,
            requester_name=locked.requester_name,
            title=locked.title,
            description=locked.description,
            material=locked.material,
            color=locked.color,
            quantity=locked.quantity,
            source_link=locked.source_link,
            project_brief=locked.project_brief,
            preferred_settings=locked.preferred_settings,
            contact_email=locked.contact_email,
            contact_phone=locked.contact_phone,
            requested_filament_spool=locked.requested_filament_spool,
            estimated_minutes=locked.estimated_minutes,
            estimated_filament_grams=locked.estimated_filament_grams,
            model_file=locked.model_file,
            estimate_screenshot=locked.estimate_screenshot,
            preview_screenshot=locked.preview_screenshot,
            status=PrintRequest.Status.ACCEPTED,
            handled_by=actor,
            accepted_at=timezone.now(),
            reprint_of=root,
        )
        audit.record(
            actor,
            "print.reprinted",
            makerspace=locked.bucket.makerspace,
            target=clone,
            meta={
                "original_id": root.id,
                "reprinted_from_id": locked.id,
                "reprint_id": clone.id,
            },
        )
        return clone
