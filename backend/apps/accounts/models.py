from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        SUPERADMIN = "superadmin", "Super Admin"
        ADMIN = "admin", "Admin"
        GUEST_ADMIN = "guest_admin", "Guest Admin"
        REQUESTER = "requester", "Requester"

    class AccessStatus(models.TextChoices):
        ACTIVE = "active", "Active"
        RESTRICTED = "restricted", "Restricted"
        SUSPENDED = "suspended", "Suspended"

    phone = models.CharField(max_length=32, blank=True)
    external_checkin_user_id = models.CharField(max_length=128, blank=True)
    role = models.CharField(
        max_length=32,
        choices=Role.choices,
        default=Role.REQUESTER,
    )
    access_status = models.CharField(
        max_length=32,
        choices=AccessStatus.choices,
        default=AccessStatus.ACTIVE,
    )
    restriction_reason = models.TextField(blank=True)
