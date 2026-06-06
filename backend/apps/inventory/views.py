from django.http import Http404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.generics import ListAPIView

from apps.inventory.serializers import (
    PublicMakerspaceSerializer,
    PublicProductSerializer,
)
from apps.makerspaces.models import Makerspace


@extend_schema(
    description="List makerspaces that have public inventory enabled.",
    responses=PublicMakerspaceSerializer(many=True),
)
class PublicMakerspaceListView(ListAPIView):
    serializer_class = PublicMakerspaceSerializer
    pagination_class = None

    def get_queryset(self):
        return Makerspace.objects.filter(
            public_inventory_enabled=True,
        ).order_by("name")


@extend_schema(
    description="List public inventory products for a public makerspace.",
    parameters=[
        OpenApiParameter(
            name="makerspace_slug",
            type=str,
            location=OpenApiParameter.PATH,
            description="Public makerspace slug.",
        ),
    ],
    responses=PublicProductSerializer(many=True),
)
class PublicInventoryListView(ListAPIView):
    serializer_class = PublicProductSerializer

    def get_queryset(self):
        try:
            makerspace = Makerspace.objects.get(slug=self.kwargs["makerspace_slug"])
        except Makerspace.DoesNotExist as exc:
            raise Http404 from exc

        if not makerspace.public_inventory_enabled:
            raise Http404

        return makerspace.products.filter(
            is_public=True,
            is_archived=False,
        ).order_by("name")
