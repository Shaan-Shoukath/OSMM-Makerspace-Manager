import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.makerspaces.models import Makerspace, MakerspaceMembership

pytestmark = pytest.mark.django_db


def make_user(username, **kwargs):
    return get_user_model().objects.create_user(
        username=username,
        email=f"{username}@e.com",
        access_status=User.AccessStatus.ACTIVE,
        **kwargs,
    )


def test_non_superadmin_staff_is_denied_from_django_admin_index():
    user = make_user(
        "admin-denied-manager",
        role=User.Role.SPACE_MANAGER,
        is_staff=True,
    )
    client = Client()
    client.force_login(user)

    response = client.get("/admin/")

    assert response.status_code == 403


def test_superadmin_is_allowed_to_django_admin_index():
    user = make_user(
        "admin-allowed-superadmin",
        role=User.Role.SUPERADMIN,
        is_staff=True,
        is_superuser=True,
    )
    client = Client()
    client.force_login(user)

    response = client.get("/admin/")

    assert response.status_code == 200


def test_react_staff_admin_api_path_is_not_gated_by_django_admin_middleware():
    makerspace = Makerspace.objects.create(name="API Staff", slug="api-staff")
    user = make_user(
        "api-staff-manager",
        role=User.Role.SPACE_MANAGER,
        is_staff=True,
    )
    MakerspaceMembership.objects.create(
        user=user,
        makerspace=makerspace,
        role=MakerspaceMembership.Role.SPACE_MANAGER,
    )
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.get("/api/v1/admin/makerspaces")

    assert response.status_code == 200
