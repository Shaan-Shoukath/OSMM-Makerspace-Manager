from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from apps.inventory.public_availability import get_public_availability


AVAILABILITY_SCHEMA = {
    "type": "object",
    "nullable": True,
    "properties": {
        "mode": {
            "type": "string",
            "enum": ["status_only", "exact_count"],
        },
        "label": {
            "type": "string",
            "enum": ["Available", "Limited", "Unavailable"],
        },
        "count": {"type": "integer", "minimum": 0},
    },
    "required": ["mode"],
}


class PublicProductSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(read_only=True)
    description = serializers.CharField(read_only=True)
    image_url = serializers.URLField(allow_blank=True, read_only=True)
    availability = serializers.SerializerMethodField()

    @extend_schema_field(AVAILABILITY_SCHEMA)
    def get_availability(self, product):
        return get_public_availability(product)


class PublicMakerspaceSerializer(serializers.Serializer):
    name = serializers.CharField(read_only=True)
    slug = serializers.SlugField(read_only=True)
    location = serializers.CharField(read_only=True)
