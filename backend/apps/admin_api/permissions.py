from rest_framework.permissions import BasePermission

from apps.accounts import rbac
from apps.accounts.models import User


def active_user(user):
    # `must_change_password` (the default super123 seed) must NOT be able to reach
    # protected staff/admin endpoints over the API before rotating — only the
    # IsAuthenticated rotation path (/auth/change-password, /auth/me) stays open.
    return bool(
        user
        and user.is_authenticated
        and user.is_active
        and user.access_status == User.AccessStatus.ACTIVE
        and not getattr(user, "must_change_password", False)
    )


class IsActiveStaff(BasePermission):
    def has_permission(self, request, view):
        return active_user(getattr(request, "user", None))


class IsActiveSuperAdmin(BasePermission):
    def has_permission(self, request, view):
        user = getattr(request, "user", None)
        return active_user(user) and (
            user.is_superuser or user.role == User.Role.SUPERADMIN
        )


def require_action(user, action, makerspace_id):
    if not rbac.can(user, action, makerspace_id):
        from rest_framework.exceptions import PermissionDenied

        raise PermissionDenied()

