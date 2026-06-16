from django.contrib.auth.hashers import make_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils.crypto import get_random_string
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts import rbac
from apps.accounts.models import User
from apps.admin_api.permissions import IsActiveStaff, IsActiveSuperAdmin
from apps.admin_api.serializers_users import (
    AuditLogSerializer,
    ResetPasswordRequestSerializer,
    ResetPasswordResponseSerializer,
    RestrictUserSerializer,
    StaffCreateSerializer,
    StaffMembershipSerializer,
    UserSerializer,
)
from apps.audit import services as audit
from apps.audit.models import AuditLog
from apps.makerspaces.models import Makerspace, MakerspaceMembership
from apps.openapi import RESTRICT_USER_EXAMPLE


@extend_schema(tags=["Admin users"], summary="List or create staff memberships")
class StaffListCreateView(generics.ListCreateAPIView):
    serializer_class = StaffMembershipSerializer
    permission_classes = [IsActiveStaff]

    def get_queryset(self):
        target_role = self.kwargs["role"]
        scope = rbac.makerspaces_for_action(self.request.user, rbac.Action.MANAGE_STAFF)
        queryset = MakerspaceMembership.objects.select_related("user", "makerspace").filter(
            role=target_role
        )
        if scope is rbac.ALL:
            queryset = rbac.hide_from_superadmin(
                self.request.user,
                queryset,
                field="makerspace_id",
            )
            return queryset.order_by("user__username")
        if target_role in (
            MakerspaceMembership.Role.PRINT_MANAGER,
            MakerspaceMembership.Role.INVENTORY_MANAGER,
        ):
            manage_scope = rbac.makerspaces_for_action(
                self.request.user,
                rbac.Action.MANAGE_MAKERSPACE,
            )
            if manage_scope is rbac.ALL:
                return queryset.order_by("user__username")
            return queryset.filter(makerspace_id__in=manage_scope).order_by(
                "user__username"
            )
        return queryset.none()

    def create(self, request, *args, **kwargs):
        serializer = StaffCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        target_role = self.kwargs["role"]
        if data["role"] != target_role:
            raise ValidationError({"role": "Role does not match endpoint."})
        if not _can_create_staff_role(request.user, target_role, data["makerspace_id"]):
            raise PermissionDenied()
        # A superadmin can target any makerspace_id, including a nonexistent one. Validate
        # before writing: otherwise get_or_create commits the user, then the membership FK
        # fails -> 500 and an orphaned staff account. Wrap both writes in one transaction so
        # a membership failure rolls back the user creation too.
        if not Makerspace.objects.filter(pk=data["makerspace_id"]).exists():
            raise ValidationError({"makerspace_id": "Makerspace does not exist."})
        with transaction.atomic():
            user, created = User.objects.get_or_create(
                username=data["username"],
                defaults={
                    "email": data.get("email", ""),
                    "first_name": data.get("first_name", ""),
                    "last_name": data.get("last_name", ""),
                    "role": _global_role_for_membership(target_role),
                    "password": make_password(data.get("password") or get_random_string(32)),
                },
            )
            membership, _ = MakerspaceMembership.objects.update_or_create(
                user=user,
                makerspace_id=data["makerspace_id"],
                defaults={"role": target_role},
            )
        audit.record(
            request.user,
            "staff.created" if created else "staff.membership_updated",
            makerspace=membership.makerspace,
            target=user,
            meta={"membership_role": target_role},
        )
        return Response(StaffMembershipSerializer(membership).data, status=201)


def _global_role_for_membership(target_role):
    if target_role == MakerspaceMembership.Role.SPACE_MANAGER:
        return User.Role.SPACE_MANAGER
    if target_role == MakerspaceMembership.Role.GUEST_ADMIN:
        return User.Role.GUEST_ADMIN
    if target_role == MakerspaceMembership.Role.INVENTORY_MANAGER:
        return User.Role.REQUESTER
    return User.Role.REQUESTER


def _can_create_staff_role(user, target_role, makerspace_id):
    if user.is_superuser or user.role == User.Role.SUPERADMIN:
        return True
    if target_role not in (
        MakerspaceMembership.Role.PRINT_MANAGER,
        MakerspaceMembership.Role.INVENTORY_MANAGER,
    ):
        return False
    return rbac.can(user, rbac.Action.MANAGE_MAKERSPACE, makerspace_id)


class RestrictUserView(APIView):
    permission_classes = [IsActiveSuperAdmin]

    @extend_schema(
        tags=["Admin users"],
        summary="Restrict or suspend a user",
        request=RestrictUserSerializer,
        responses={200: UserSerializer},
        examples=[RESTRICT_USER_EXAMPLE],
    )
    def post(self, request, pk, *args, **kwargs):
        user = get_object_or_404(User, pk=pk)
        serializer = RestrictUserSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user.access_status = serializer.validated_data["status"]
        user.restriction_reason = serializer.validated_data["reason"]
        user.save(update_fields=["access_status", "restriction_reason"])
        audit.record(
            request.user,
            "user.access_restricted",
            target=user,
            meta={"status": user.access_status, "reason": user.restriction_reason},
        )
        return Response(UserSerializer(user).data)


class ResetUserPasswordView(APIView):
    permission_classes = [IsActiveStaff]

    @extend_schema(
        tags=["Admin users"],
        summary="Reset a staff user's password (temp + force change)",
        request=ResetPasswordRequestSerializer,
        responses={200: ResetPasswordResponseSerializer},
    )
    def post(self, request, pk, *args, **kwargs):
        actor = request.user
        is_superadmin = actor.is_superuser or actor.role == User.Role.SUPERADMIN
        # 404-before-403: a non-superadmin may only act on users inside their
        # MANAGE_MAKERSPACE scope, so a nonexistent OR out-of-scope pk both return 404 —
        # no probing user existence by id via a 403-vs-404 difference.
        if is_superadmin:
            target = get_object_or_404(User, pk=pk)
        else:
            scope = rbac.makerspaces_for_action(actor, rbac.Action.MANAGE_MAKERSPACE)
            base = User.objects.all()
            if scope is not rbac.ALL:
                base = base.filter(
                    makerspace_memberships__makerspace_id__in=scope
                ).distinct()
            target = get_object_or_404(base, pk=pk)
        # Never reset a superadmin via this endpoint.
        if target.is_superuser or target.role == User.Role.SUPERADMIN:
            raise PermissionDenied("Cannot reset a superadmin's password here.")
        # EXISTENTIAL hidden-space Space-Manager block (applies to ALL actors incl. superadmin):
        # if the target is a SPACE_MANAGER of ANY makerspace that disabled superadmin access,
        # nobody may reset them in-app (they self-recover by email, or the space re-enables access).
        if MakerspaceMembership.objects.filter(
            user=target,
            role=MakerspaceMembership.Role.SPACE_MANAGER,
            makerspace__superadmin_access_enabled=False,
        ).exists():
            raise PermissionDenied(
                "This user is a Space Manager of a makerspace that turned off superadmin access; "
                "they must self-recover via the forgot-password email, or the makerspace must re-enable access."
            )
        if not is_superadmin:
            memberships = MakerspaceMembership.objects.filter(user=target)
            if not memberships.exists():
                raise PermissionDenied("You can only reset staff in your makerspaces.")
            scope = rbac.makerspaces_for_action(actor, rbac.Action.MANAGE_MAKERSPACE)
            if scope is not rbac.ALL:
                target_ms = set(memberships.values_list("makerspace_id", flat=True))
                if not target_ms.issubset(scope):
                    raise PermissionDenied(
                        "This user also belongs to a makerspace outside your authority."
                    )
            # No peer Space-Manager takeover: a makerspace admin cannot reset another Space Manager.
            if memberships.filter(role=MakerspaceMembership.Role.SPACE_MANAGER).exists():
                raise PermissionDenied("Cannot reset another Space Manager's password.")
        serializer = ResetPasswordRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        password = serializer.validated_data.get("password")
        if password:
            try:
                validate_password(password, user=target)
            except DjangoValidationError as exc:
                raise ValidationError({"password": list(exc.messages)}) from exc
        else:
            # auto-generate a temp password that passes the active validators (retry a few times)
            for _ in range(5):
                candidate = get_random_string(12)
                try:
                    validate_password(candidate, user=target)
                    password = candidate
                    break
                except DjangoValidationError:
                    continue
            if not password:
                password = get_random_string(16)
        target.set_password(password)
        target.must_change_password = True
        target.save(update_fields=["password", "must_change_password"])
        # Revoke outstanding refresh tokens so a session that authenticated with the
        # OLD password can't persist after an admin-forced reset.
        from apps.accounts.views import _blacklist_outstanding_tokens

        _blacklist_outstanding_tokens(target)
        audit.record(
            actor,
            "user.password_reset",
            target=target,
            meta={"by_superadmin": is_superadmin},
        )
        return Response(
            ResetPasswordResponseSerializer(
                {"username": target.username, "temporary_password": password}
            ).data
        )


class RestoreUserAccessView(APIView):
    permission_classes = [IsActiveSuperAdmin]

    @extend_schema(tags=["Admin users"], summary="Restore user access", request=None, responses={200: UserSerializer})
    def post(self, request, pk, *args, **kwargs):
        user = get_object_or_404(User, pk=pk)
        user.access_status = User.AccessStatus.ACTIVE
        user.restriction_reason = ""
        user.save(update_fields=["access_status", "restriction_reason"])
        audit.record(request.user, "user.access_restored", target=user)
        return Response(UserSerializer(user).data)


class AuditLogPagination(PageNumberPagination):
    page_size = 24


@extend_schema(tags=["Admin users"], summary="List audit log entries", parameters=[
    OpenApiParameter("makerspace", int, OpenApiParameter.QUERY), OpenApiParameter("action", str, OpenApiParameter.QUERY),
    OpenApiParameter("target_type", str, OpenApiParameter.QUERY), OpenApiParameter("target_id", str, OpenApiParameter.QUERY),
])
class AuditLogListView(generics.ListAPIView):
    serializer_class = AuditLogSerializer
    permission_classes = [IsActiveStaff]
    pagination_class = AuditLogPagination

    def get_queryset(self):
        queryset = AuditLog.objects.select_related("actor", "makerspace").order_by("-created_at")
        queryset = rbac.scope_by_action(self.request.user, rbac.Action.VIEW_AUDIT, queryset)
        queryset = rbac.hide_from_superadmin(self.request.user, queryset, field="makerspace_id")
        makerspace_id = self.request.query_params.get("makerspace")
        action = self.request.query_params.get("action")
        target_type, target_id = (
            self.request.query_params.get("target_type"),
            self.request.query_params.get("target_id"),
        )
        filters = {}
        if makerspace_id:
            filters["makerspace_id"] = makerspace_id
        if action:
            filters["action"] = action
        if target_type:
            filters["target_type"] = target_type
        if target_id:
            filters["target_id"] = target_id
        if filters:
            queryset = queryset.filter(**filters)
        return queryset
