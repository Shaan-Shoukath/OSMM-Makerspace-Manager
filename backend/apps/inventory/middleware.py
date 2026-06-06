import hashlib
import hmac
import time

from django.conf import settings
from django.http import JsonResponse


class FrontendHMACMiddleware:
    """Optionally validate signed frontend requests for selected API paths."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not self._should_validate(request):
            return self.get_response(request)

        if not self._has_valid_signature(request):
            return JsonResponse(
                {"detail": "Invalid frontend signature."},
                status=401,
            )

        return self.get_response(request)

    def _should_validate(self, request):
        if request.method == "OPTIONS":
            return False

        if not settings.HMAC_CLIENT_ID or not settings.HMAC_SECRET:
            return False

        return any(
            request.path.startswith(prefix)
            for prefix in settings.HMAC_PROTECTED_PATH_PREFIXES
        )

    def _has_valid_signature(self, request):
        client_id = request.headers.get("X-Client-Id", "")
        timestamp = request.headers.get("X-Timestamp", "")
        signature = request.headers.get("X-Signature", "")

        if not client_id or not timestamp or not signature:
            return False

        if not hmac.compare_digest(client_id, settings.HMAC_CLIENT_ID):
            return False

        try:
            request_time = int(timestamp)
        except ValueError:
            return False

        skew = abs(int(time.time()) - request_time)
        if skew > settings.HMAC_MAX_CLOCK_SKEW_SECONDS:
            return False

        expected_signature = self._signature_for(request, timestamp)
        return hmac.compare_digest(signature, expected_signature)

    def _signature_for(self, request, timestamp):
        message = b"\n".join(
            [
                request.method.upper().encode("utf-8"),
                request.get_full_path().encode("utf-8"),
                timestamp.encode("utf-8"),
                request.body,
            ]
        )
        return hmac.new(
            settings.HMAC_SECRET.encode("utf-8"),
            message,
            hashlib.sha256,
        ).hexdigest()
