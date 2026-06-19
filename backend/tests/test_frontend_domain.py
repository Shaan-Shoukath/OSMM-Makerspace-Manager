import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.urls import reverse

from apps.makerspaces.models import Makerspace
from tests.return_helpers import authenticated_client, make_member, make_space

pytestmark = pytest.mark.django_db


def makerspace_detail_url(makerspace):
    return reverse("admin-makerspace", kwargs={"pk": makerspace.id})


def test_makerspace_save_normalizes_frontend_domain():
    makerspace = Makerspace.objects.create(
        name="Alpha",
        slug="frontend-normalize-alpha",
        frontend_domain="  Alpha.COM ",
    )

    assert makerspace.frontend_domain == "alpha.com"

    makerspace.frontend_domain = ""
    makerspace.save(update_fields=["frontend_domain"])

    assert makerspace.frontend_domain is None


def test_makerspace_frontend_domain_is_unique_case_insensitively():
    with pytest.raises(IntegrityError), transaction.atomic():
        Makerspace.objects.bulk_create(
            [
                Makerspace(
                    name="Alpha",
                    slug="frontend-ci-alpha",
                    public_code="CIA1",
                    frontend_domain="alpha.com",
                ),
                Makerspace(
                    name="Alpha Duplicate",
                    slug="frontend-ci-alpha-dupe",
                    public_code="CIA2",
                    frontend_domain="Alpha.com",
                ),
            ]
        )


def test_many_makerspaces_can_have_null_frontend_domain():
    first = make_space("frontend-null-one")
    second = make_space("frontend-null-two")

    assert first.frontend_domain is None
    assert second.frontend_domain is None


def test_hidden_from_central_directory_requires_frontend_domain_in_model_validation():
    makerspace = Makerspace(
        name="Hidden",
        slug="frontend-hidden-invalid",
        hidden_from_central_directory=True,
    )

    with pytest.raises(ValidationError):
        makerspace.full_clean()


def test_hidden_from_central_directory_requires_frontend_domain_in_database():
    makerspace = make_space("frontend-hidden-db-invalid")

    with pytest.raises(IntegrityError), transaction.atomic():
        Makerspace.objects.filter(pk=makerspace.pk).update(
            hidden_from_central_directory=True,
            frontend_domain=None,
        )


def test_serializer_rejects_hiding_without_effective_frontend_domain():
    makerspace = make_space("frontend-api-hidden-invalid")
    manager = make_member("frontend-api-hidden-invalid-manager", makerspace)

    response = authenticated_client(manager).patch(
        makerspace_detail_url(makerspace),
        {"hidden_from_central_directory": True},
        format="json",
    )

    assert response.status_code == 400
    makerspace.refresh_from_db()
    assert makerspace.hidden_from_central_directory is False


def test_serializer_clearing_frontend_domain_also_unhides_makerspace():
    makerspace = make_space("frontend-api-clear")
    makerspace.frontend_domain = "alpha.example.com"
    makerspace.hidden_from_central_directory = True
    makerspace.save(update_fields=["frontend_domain", "hidden_from_central_directory"])
    manager = make_member("frontend-api-clear-manager", makerspace)

    response = authenticated_client(manager).patch(
        makerspace_detail_url(makerspace),
        {"frontend_domain": ""},
        format="json",
    )

    assert response.status_code == 200
    makerspace.refresh_from_db()
    assert makerspace.frontend_domain is None
    assert makerspace.hidden_from_central_directory is False


def test_serializer_rejects_duplicate_frontend_domain_case_insensitively():
    existing = make_space("frontend-api-existing")
    existing.frontend_domain = "alpha.example.com"
    existing.save(update_fields=["frontend_domain"])
    target = make_space("frontend-api-target")
    manager = make_member("frontend-api-target-manager", target)

    response = authenticated_client(manager).patch(
        makerspace_detail_url(target),
        {"frontend_domain": " Alpha.EXAMPLE.com "},
        format="json",
    )

    assert response.status_code == 400
    assert "frontend_domain" in response.data
    target.refresh_from_db()
    assert target.frontend_domain is None
