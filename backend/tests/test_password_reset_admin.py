import pytest
from django.urls import reverse

from apps.accounts.models import User
from apps.makerspaces.models import MakerspaceMembership
from tests.return_helpers import authenticated_client, make_member, make_space, make_user

pytestmark = pytest.mark.django_db


def make_superadmin(username):
    return make_user(
        username,
        role=User.Role.SUPERADMIN,
        access_status=User.AccessStatus.ACTIVE,
    )


def reset_password_url(user):
    return reverse("admin-user-reset-password", kwargs={"pk": user.id})


def test_makerspace_admin_resets_managed_staff():
    space = make_space("admin-reset-managed")
    admin = make_member("admin-reset-manager", space)
    target = make_member(
        "admin-reset-inventory",
        space,
        membership_role=MakerspaceMembership.Role.INVENTORY_MANAGER,
        role=User.Role.REQUESTER,
    )
    client = authenticated_client(admin)

    first = client.post(reset_password_url(target), {}, format="json")
    target.refresh_from_db()
    second = client.post(reset_password_url(target), {}, format="json")
    target.refresh_from_db()

    assert first.status_code == 200
    assert first.data["temporary_password"]
    assert target.must_change_password is True
    assert second.status_code == 200
    assert second.data["temporary_password"]


def test_cannot_reset_superadmin_target():
    space = make_space("admin-reset-super-target")
    actor = make_member("admin-reset-super-actor", space)
    target = make_superadmin("admin-reset-super-target")

    response = authenticated_client(actor).post(reset_password_url(target), {}, format="json")

    assert response.status_code == 403


def test_superadmin_cannot_reset_hidden_space_space_manager():
    hidden_space = make_space("admin-reset-hidden")
    hidden_space.superadmin_access_enabled = False
    hidden_space.save(update_fields=["superadmin_access_enabled"])
    target = make_member("admin-reset-hidden-manager", hidden_space)
    superadmin = make_superadmin("admin-reset-hidden-super")

    response = authenticated_client(superadmin).post(
        reset_password_url(target),
        {},
        format="json",
    )

    assert response.status_code == 403


def test_non_superadmin_cannot_reset_peer_space_manager():
    space = make_space("admin-reset-peer")
    actor = make_member("admin-reset-peer-actor", space)
    target = make_member("admin-reset-peer-target", space)

    response = authenticated_client(actor).post(reset_password_url(target), {}, format="json")

    assert response.status_code == 403


def test_non_superadmin_cannot_reset_user_outside_scope():
    space_a = make_space("admin-reset-scope-a")
    space_b = make_space("admin-reset-scope-b")
    actor = make_member("admin-reset-scope-actor", space_a)
    target = make_member(
        "admin-reset-scope-target",
        space_b,
        membership_role=MakerspaceMembership.Role.INVENTORY_MANAGER,
        role=User.Role.REQUESTER,
    )

    response = authenticated_client(actor).post(reset_password_url(target), {}, format="json")

    assert response.status_code == 403
