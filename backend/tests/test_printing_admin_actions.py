import pytest
from django.contrib import messages
from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.test import Client
from django.urls import reverse

from apps.accounts.models import User
from apps.printing.models import PrintRequest
from tests.test_printing import make_bucket, make_request, make_space, make_user

pytestmark = pytest.mark.django_db


def make_superadmin(username="printing-admin"):
    return get_user_model().objects.create_user(
        username=username,
        email=f"{username}@e.com",
        role=User.Role.SUPERADMIN,
        access_status=User.AccessStatus.ACTIVE,
        is_staff=True,
        is_superuser=True,
    )


def print_request_changelist_url():
    return reverse("admin:printing_printrequest_changelist")


def admin_action_payload(action_name, print_request, **extra):
    return {
        "action": action_name,
        ACTION_CHECKBOX_NAME: [str(print_request.pk)],
        "select_across": "0",
        "index": "0",
        **extra,
    }


def logged_in_superadmin_client():
    client = Client()
    client.force_login(make_superadmin())
    return client


def make_pending_print_request(slug, requester_username):
    makerspace = make_space(slug)
    bucket = make_bucket(makerspace)
    requester = make_user(
        requester_username,
        access_status=User.AccessStatus.ACTIVE,
    )
    return make_request(bucket, requester)


def test_accept_selected_moves_pending_request_to_accepted():
    print_request = make_pending_print_request(
        "admin-accept-printing",
        "admin-accept-requester",
    )
    client = logged_in_superadmin_client()

    response = client.post(
        print_request_changelist_url(),
        admin_action_payload("accept_selected", print_request),
        follow=True,
    )

    assert response.status_code == 200
    print_request.refresh_from_db()
    assert print_request.status == PrintRequest.Status.ACCEPTED


def test_reject_selected_with_reason_rejects_and_stores_reason():
    print_request = make_pending_print_request(
        "admin-reject-printing",
        "admin-reject-requester",
    )
    client = logged_in_superadmin_client()

    response = client.post(
        print_request_changelist_url(),
        admin_action_payload(
            "reject_selected",
            print_request,
            apply="1",
            reason="Needs a manifold STL.",
        ),
        follow=True,
    )

    assert response.status_code == 200
    print_request.refresh_from_db()
    assert print_request.status == PrintRequest.Status.REJECTED
    assert print_request.reason == "Needs a manifold STL."


def test_reject_selected_with_empty_reason_does_not_change_status_and_reports_error():
    print_request = make_pending_print_request(
        "admin-reject-empty-printing",
        "admin-reject-empty-requester",
    )
    client = logged_in_superadmin_client()

    response = client.post(
        print_request_changelist_url(),
        admin_action_payload(
            "reject_selected",
            print_request,
            apply="1",
            reason="   ",
        ),
        follow=True,
    )

    assert response.status_code == 200
    print_request.refresh_from_db()
    assert print_request.status == PrintRequest.Status.PENDING

    collected = list(get_messages(response.wsgi_request))
    assert any(
        message.level == messages.ERROR
        and "Rejection reason is required." in str(message)
        for message in collected
    )


def test_start_selected_accepts_decimal_filament_estimate():
    """Regression: estimated_filament_grams is a 2-decimal field; the start action
    must validate via PrintStartSerializer, not reject fractional grams."""
    from decimal import Decimal

    from apps.printing.models import FilamentSpool, PrintPrinter

    makerspace = make_space("admin-start-printing")
    bucket = make_bucket(makerspace)
    requester = make_user("admin-start-requester", access_status=User.AccessStatus.ACTIVE)
    print_request = make_request(
        bucket, requester, title="Decimal", status=PrintRequest.Status.ACCEPTED
    )
    printer = PrintPrinter.objects.create(makerspace=makerspace, name="Prusa MK4")
    spool = FilamentSpool.objects.create(
        makerspace=makerspace,
        printer=printer,
        material="PETG",
        color="orange",
        initial_weight_grams=1000,
        remaining_weight_grams=640,
    )

    client = logged_in_superadmin_client()
    response = client.post(
        print_request_changelist_url(),
        admin_action_payload(
            "start_selected",
            print_request,
            apply="1",
            **{
                f"printer_id_{print_request.pk}": str(printer.pk),
                f"filament_spool_id_{print_request.pk}": str(spool.pk),
                f"estimated_minutes_{print_request.pk}": "90",
                f"estimated_filament_grams_{print_request.pk}": "12.5",
            },
        ),
    )

    assert response.status_code == 302
    print_request.refresh_from_db()
    assert print_request.status == PrintRequest.Status.PRINTING
    assert print_request.estimated_filament_grams == Decimal("12.5")
