from django.conf import settings
from drf_spectacular.utils import OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.accounts.auth_cookies import (
    assert_csrf,
    clear_refresh_cookies,
    set_refresh_cookies,
)
from apps.accounts.models import User
from apps.accounts.serializers import LoginSerializer, user_payload
from apps.openapi import LOGIN_EXAMPLE


UserPayloadSerializer = inline_serializer(
    name="AuthUserPayload",
    fields={
        "id": serializers.IntegerField(),
        "username": serializers.CharField(),
        "email": serializers.EmailField(),
        "role": serializers.CharField(),
        "is_superuser": serializers.BooleanField(),
        # documented loosely: list of {id, slug, role} membership objects.
        "makerspaces": serializers.ListField(child=serializers.DictField()),
    },
)
LoginRequestSerializer = inline_serializer(
    name="LoginRequest",
    fields={
        "username": serializers.CharField(),
        "password": serializers.CharField(write_only=True),
    },
)
LoginResponseSerializer = inline_serializer(
    name="LoginResponse",
    fields={
        "access": serializers.CharField(),
        "user": UserPayloadSerializer,
    },
)
RefreshResponseSerializer = inline_serializer(
    name="RefreshResponse",
    fields={"access": serializers.CharField()},
)
LogoutResponseSerializer = inline_serializer(
    name="LogoutResponse",
    fields={"detail": serializers.CharField()},
)


class LoginView(TokenObtainPairView):
    # Explicit under deny-by-default (DEFAULT_PERMISSION_CLASSES=IsAuthenticated):
    # obtaining a token must be open. RefreshView inherits simplejwt's AllowAny.
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"
    serializer_class = LoginSerializer

    @extend_schema(
        tags=["Auth"],
        summary="Log in staff user",
        auth=[],
        request=LoginRequestSerializer,
        responses={
            200: LoginResponseSerializer,
            401: OpenApiResponse(description="Invalid credentials or inactive account."),
            403: OpenApiResponse(description="Account access is restricted."),
        },
        examples=[LOGIN_EXAMPLE],
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        refresh = data.pop("refresh")
        response = Response({"access": data["access"], "user": data["user"]})
        set_refresh_cookies(response, refresh, request)
        return response


def _refresh_user_is_active(token_str):
    """Return False if the refresh token's user is suspended/restricted/inactive."""
    try:
        token = RefreshToken(token_str)
    except TokenError:
        return True  # invalid token: let the serializer reject it as 401, not 403
    user = User.objects.filter(pk=token.get("user_id")).first()
    return bool(
        user and user.is_active and user.access_status == User.AccessStatus.ACTIVE
    )


class RefreshView(TokenRefreshView):
    @extend_schema(
        tags=["Auth"],
        summary="Refresh access token",
        auth=[],
        request=None,
        responses={
            200: RefreshResponseSerializer,
            401: OpenApiResponse(description="Missing, invalid, or replayed refresh token."),
            403: OpenApiResponse(description="CSRF check failed or account restricted."),
        },
    )
    def post(self, request, *args, **kwargs):
        assert_csrf(request)  # header presence + Origin allowlist (CSRF defense)
        cookie = request.COOKIES.get(settings.AUTH_REFRESH_COOKIE)
        if not cookie:
            raise InvalidToken("No refresh cookie.")
        if not _refresh_user_is_active(cookie):  # review fix #5
            response = Response({"detail": "Account access is restricted."}, status=403)
            clear_refresh_cookies(response)
            return response
        serializer = self.get_serializer(data={"refresh": cookie})
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as exc:
            raise InvalidToken(str(exc)) from exc
        data = serializer.validated_data
        response = Response({"access": data["access"]})
        new_refresh = data.get("refresh")
        if new_refresh:
            set_refresh_cookies(response, new_refresh, request)
        return response


class LogoutView(APIView):
    permission_classes = [AllowAny]  # cookie-based; protected by assert_csrf below

    @extend_schema(
        tags=["Auth"],
        summary="Log out and clear refresh cookie",
        auth=[],
        request=None,
        responses={
            200: LogoutResponseSerializer,
            401: OpenApiResponse(description="Refresh token could not be blacklisted."),
            403: OpenApiResponse(description="CSRF check failed."),
        },
    )
    def post(self, request, *args, **kwargs):
        assert_csrf(request)  # review fix #8: logout must not be CSRF-able
        cookie = request.COOKIES.get(settings.AUTH_REFRESH_COOKIE)
        if cookie:
            try:
                RefreshToken(cookie).blacklist()
            except TokenError:
                pass
        response = Response({"detail": "Logged out."})
        clear_refresh_cookies(response)
        return response


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Auth"],
        summary="Get current staff profile",
        request=None,
        responses={
            200: UserPayloadSerializer,
            401: OpenApiResponse(description="Authentication credentials were not provided."),
        },
    )
    def get(self, request, *args, **kwargs):
        return Response(user_payload(request.user))
