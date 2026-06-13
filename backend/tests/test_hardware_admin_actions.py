import uuid

import pytest
from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.test import Client
from django.urls import reverse

from apps.accounts.models import User
from apps.hardware_requests.models import HardwareRequest, HardwareRequestItem
from apps.inventory.models import InventoryProduct
from apps.makerspaces.models import Makerspace

pytestmark = pytest.mark.django_db


def make_user(username, **kwargs):
    return get_user_model().objects.create_user(
        username=username,
        email=f"{username}@e.com",
        access_status=User.AccessStatus.ACTIVE,
        **kwargs,
    )


def make_superadmin(username="hardware-action-superadmin"):
    return make_user(
        username,
        role=User.Role.SUPERADMIN,
        is_staff=True,
        is_superuser=True,
    )


def make_hardware_request(status=HardwareRequest.Status.PENDING_APPROVAL):
    makerspace = Makerspace.objects.create(
        name=f"Admin Hardware {uuid.uuid4().hex[:8]}",
        slug=f"admin-hardware-{uuid.uuid4().hex[:8]}",
    )
    requester = make_user(
        f"admin-hardware-requester-{uuid.uuid4().hex[:8]}",
    )
    product = InventoryProduct.objects.create(
        makerspace=makerspace,
        name=f"Logic Analyzer {uuid.uuid4().hex[:8]}",
        description="Bench diagnostics",
        total_quantity=5,
        available_quantity=5,
        reserved_quantity=0,
        is_public=True,
        is_archived=False,
    )
    hardware_request = HardwareRequest.objects.create(
        makerspace=makerspace,
        requester=requester,
        requester_username=requester.username,
        status=status,
    )
    HardwareRequestItem.objects.create(
        request=hardware_request,
        product=product,
        requested_quantity=1,
    )
    return hardware_request


def admin_client(user):
    client = Client()
    client.force_login(user)
    return client


def changelist_url():
    return reverse("admin:hardware_requests_hardwarerequest_changelist")


def action_payload(action, hardware_request, **extra):
    return {
        "action": action,
        ACTION_CHECKBOX_NAME: [str(hardware_request.pk)],
        **extra,
    }


def test_accept_action_moves_pending_request_to_accepted():
    superadmin = make_superadmin()
    hardware_request = make_hardware_request()

    response = admin_client(superadmin).post(
        changelist_url(),
        action_payload("accept_selected", hardware_request),
    )

    assert response.status_code == 302
    hardware_request.refresh_from_db()
    assert hardware_request.status == HardwareRequest.Status.ACCEPTED


def test_reject_action_with_reason_moves_pending_request_to_rejected():
    superadmin = make_superadmin("hardware-reject-superadmin")
    hardware_request = make_hardware_request()

    response = admin_client(superadmin).post(
        changelist_url(),
        action_payload(
            "reject_selected",
            hardware_request,
            apply="1",
            reason="Unavailable this week.",
        ),
    )

    assert response.status_code == 302
    hardware_request.refresh_from_db()
    assert hardware_request.status == HardwareRequest.Status.REJECTED
    assert hardware_request.rejection_reason == "Unavailable this week."


def test_reject_action_with_empty_reason_does_not_change_status_and_reports_error():
    superadmin = make_superadmin("hardware-empty-reject-superadmin")
    hardware_request = make_hardware_request()
    client = admin_client(superadmin)

    response = client.post(
        changelist_url(),
        action_payload(
            "reject_selected",
            hardware_request,
            apply="1",
            reason="   ",
        ),
        follow=True,
    )

    hardware_request.refresh_from_db()
    assert hardware_request.status == HardwareRequest.Status.PENDING_APPROVAL
    messages = [str(message) for message in get_messages(response.wsgi_request)]
    assert "Rejection reason is required." in messages


def test_hardware_request_admin_blocks_direct_add_and_delete():
    """Regression: requests are workflow-driven; the admin must not expose
    direct add (broken readonly form) or delete (bypasses reservation/audit)."""
    superadmin = make_superadmin("hardware-add-delete-superadmin")
    # has_*_permission=False raises PermissionDenied (rendered as 403); the test
    # client must not re-raise it.
    client = Client(raise_request_exception=False)
    client.force_login(superadmin)

    add_url = reverse("admin:hardware_requests_hardwarerequest_add")
    add_response = client.get(add_url)
    assert add_response.status_code == 403

    hardware_request = make_hardware_request()
    delete_url = reverse(
        "admin:hardware_requests_hardwarerequest_delete",
        args=[hardware_request.pk],
    )
    delete_response = client.get(delete_url)
    assert delete_response.status_code == 403
