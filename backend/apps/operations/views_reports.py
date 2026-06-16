import csv
from io import BytesIO, StringIO

from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from openpyxl import Workbook
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts import rbac
from apps.admin_api.permissions import IsActiveStaff, require_action
from apps.makerspaces.guards import require_module
from apps.makerspaces.models import Makerspace
from apps.operations import ledger, reports
from apps.operations.serializers import EmptySerializer, GenericObjectSerializer, LedgerResponseSerializer


class LedgerView(APIView):
    permission_classes = [IsActiveStaff]
    serializer_class = LedgerResponseSerializer

    @extend_schema(
        tags=["Ledger"],
        summary="List outstanding inventory loans",
        request=None,
        responses={200: LedgerResponseSerializer},
    )
    def get(self, request, makerspace_id, *args, **kwargs):
        makerspace = _makerspace_for_inventory_view(request.user, makerspace_id)
        require_action(request.user, rbac.Action.VIEW_INVENTORY, makerspace.id)
        require_module(makerspace, "staff_admin")
        return Response(_ledger_payload(ledger.ledger_rows(makerspace.id)))


class AggregateLedgerView(APIView):
    permission_classes = [IsActiveStaff]
    serializer_class = LedgerResponseSerializer

    @extend_schema(
        tags=["Ledger"],
        summary="List outstanding inventory loans across all makerspaces",
        request=None,
        responses={200: LedgerResponseSerializer},
    )
    def get(self, request, *args, **kwargs):
        _require_superadmin(request.user)
        return Response(_ledger_payload(ledger.ledger_rows()))


class AnalyticsView(APIView):
    permission_classes = [IsActiveStaff]
    serializer_class = GenericObjectSerializer

    @extend_schema(tags=["Analytics"], summary="Get analytics report", request=None, responses={200: OpenApiTypes.OBJECT})
    def get(self, request, makerspace_id, report_key="summary", *args, **kwargs):
        makerspace = _makerspace_for_inventory_view(request.user, makerspace_id)
        require_action(request.user, rbac.Action.VIEW_INVENTORY, makerspace.id)
        require_module(makerspace, "reports")
        return Response(reports.report_data(report_key, makerspace.id))


class AggregateAnalyticsView(APIView):
    permission_classes = [IsActiveStaff]
    serializer_class = GenericObjectSerializer

    @extend_schema(
        tags=["Analytics"],
        summary="Get aggregate analytics report",
        request=None,
        parameters=[
            OpenApiParameter("report_key", OpenApiTypes.STR, OpenApiParameter.PATH, enum=reports.REPORT_KEYS),
        ],
        responses={200: OpenApiTypes.OBJECT},
    )
    def get(self, request, report_key="summary", *args, **kwargs):
        _require_superadmin(request.user)
        return Response(reports.report_data(report_key))


class ReportExportView(APIView):
    permission_classes = [IsActiveStaff]
    serializer_class = EmptySerializer

    @extend_schema(
        tags=["Reports"],
        summary="Export report",
        request=None,
        parameters=[
            OpenApiParameter("report_key", OpenApiTypes.STR, OpenApiParameter.PATH, enum=reports.REPORT_KEYS),
            OpenApiParameter("format", OpenApiTypes.STR, OpenApiParameter.QUERY, enum=["csv", "xlsx"]),
        ],
        responses={
            (200, "text/csv"): OpenApiTypes.STR,
            (200, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"): OpenApiTypes.BINARY,
        },
    )
    def get(self, request, makerspace_id, report_key, *args, **kwargs):
        makerspace = _makerspace_for_inventory_view(request.user, makerspace_id)
        require_action(request.user, rbac.Action.VIEW_INVENTORY, makerspace.id)
        require_module(makerspace, "reports")
        fmt = request.query_params.get("format", "csv")
        rows = reports.report_rows(report_key, makerspace.id)
        if fmt == "xlsx":
            return _xlsx_response(rows, f"{report_key}.xlsx")
        if fmt != "csv":
            raise ValidationError({"format": "Use csv or xlsx."})
        return _csv_response(rows, f"{report_key}.csv")


class AggregateReportExportView(APIView):
    permission_classes = [IsActiveStaff]
    serializer_class = EmptySerializer

    @extend_schema(
        tags=["Reports"],
        summary="Export aggregate report",
        request=None,
        parameters=[
            OpenApiParameter("report_key", OpenApiTypes.STR, OpenApiParameter.PATH, enum=reports.REPORT_KEYS),
            OpenApiParameter("format", OpenApiTypes.STR, OpenApiParameter.QUERY, enum=["csv", "xlsx"]),
        ],
        responses={
            (200, "text/csv"): OpenApiTypes.STR,
            (200, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"): OpenApiTypes.BINARY,
        },
    )
    def get(self, request, report_key, *args, **kwargs):
        _require_superadmin(request.user)
        fmt = request.query_params.get("format", "csv")
        rows = reports.report_rows(report_key)
        if fmt == "xlsx":
            return _xlsx_response(rows, f"{report_key}.xlsx")
        if fmt != "csv":
            raise ValidationError({"format": "Use csv or xlsx."})
        return _csv_response(rows, f"{report_key}.csv")


def report_data(makerspace_id, report_key):
    return reports.report_data(report_key, makerspace_id)


def report_rows(makerspace_id, report_key):
    return reports.report_rows(report_key, makerspace_id)


def _makerspace_for_inventory_view(user, makerspace_id):
    queryset = rbac.scope_by_action(user, rbac.Action.VIEW_INVENTORY, Makerspace.objects.all(), field="id")
    # Soft-hide: a superadmin must not reach a makerspace that turned off superadmin
    # access by querying it directly by id (the aggregate paths already exclude it).
    # No-op for non-superadmins, so a hidden space's own staff keep their reports.
    queryset = rbac.hide_from_superadmin(user, queryset, field="id")
    return get_object_or_404(queryset, pk=makerspace_id)


def _require_superadmin(user):
    if not (user.is_superuser or user.role == user.Role.SUPERADMIN):
        raise PermissionDenied()


def _ledger_payload(rows):
    serializer = LedgerResponseSerializer({"count": len(rows), "results": rows})
    return serializer.data


def _csv_response(rows, filename):
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerows(rows)
    response = HttpResponse(buffer.getvalue(), content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def _xlsx_response(rows, filename):
    wb = Workbook()
    ws = wb.active
    for row in rows:
        # openpyxl raises on tz-aware datetimes ("Excel does not support timezones");
        # report rows (e.g. active-loans issued_at, returns closed_at) carry aware
        # datetimes, so drop tzinfo before writing the cell.
        ws.append([_xlsx_cell(value) for value in row])
    buffer = BytesIO()
    wb.save(buffer)
    response = HttpResponse(buffer.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def _xlsx_cell(value):
    from datetime import datetime as _dt

    if isinstance(value, _dt) and value.tzinfo is not None:
        return value.replace(tzinfo=None)
    return value
