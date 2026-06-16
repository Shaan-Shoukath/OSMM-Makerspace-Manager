from django.db import transaction
from rest_framework import serializers

from apps.makerspaces.models import Makerspace
from apps.printing.models import FilamentSpool


class FilamentSpoolSummarySerializer(serializers.ModelSerializer):
    printer = serializers.IntegerField(source="printer_id", read_only=True)

    class Meta:
        model = FilamentSpool
        fields = (
            "id",
            "printer",
            "material",
            "color",
            "brand",
            "lot_code",
            "initial_weight_grams",
            "remaining_weight_grams",
            "is_active",
            "opened_at",
        )
        read_only_fields = fields


class FilamentSpoolSerializer(serializers.ModelSerializer):
    makerspace = serializers.IntegerField(source="makerspace_id")
    printer_name = serializers.CharField(source="printer.name", read_only=True)

    class Meta:
        model = FilamentSpool
        fields = (
            "id",
            "makerspace",
            "printer",
            "printer_name",
            "material",
            "color",
            "brand",
            "lot_code",
            "initial_weight_grams",
            "remaining_weight_grams",
            "is_active",
            "opened_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "printer_name", "created_at", "updated_at")

    def validate(self, attrs):
        makerspace_id = attrs.get("makerspace_id") or getattr(
            self.instance, "makerspace_id", None
        )
        printer = attrs["printer"] if "printer" in attrs else getattr(
            self.instance, "printer", None
        )
        if not makerspace_id:
            raise serializers.ValidationError({"makerspace": "This field is required."})
        if not Makerspace.objects.filter(pk=makerspace_id).exists():
            raise serializers.ValidationError({"makerspace": "Unknown makerspace."})
        if printer and printer.makerspace_id != makerspace_id:
            raise serializers.ValidationError(
                {"printer": "Printer must belong to the same makerspace."}
            )
        remaining = attrs.get(
            "remaining_weight_grams",
            getattr(self.instance, "remaining_weight_grams", None),
        )
        initial = attrs.get(
            "initial_weight_grams",
            getattr(self.instance, "initial_weight_grams", None),
        )
        if initial is not None and remaining is not None and remaining > initial:
            raise serializers.ValidationError(
                {"remaining_weight_grams": "Remaining weight cannot exceed initial weight."}
            )
        return attrs

    def create(self, validated_data):
        makerspace_id = validated_data.pop("makerspace_id")
        return FilamentSpool.objects.create(
            makerspace_id=makerspace_id,
            **validated_data,
        )

    def update(self, instance, validated_data):
        with transaction.atomic():
            locked = FilamentSpool.objects.select_for_update().get(pk=instance.pk)
            update_fields = []
            if "makerspace_id" in validated_data:
                locked.makerspace_id = validated_data.pop("makerspace_id")
                update_fields.append("makerspace")
            for attr, value in validated_data.items():
                setattr(locked, attr, value)
                update_fields.append(attr)
            if update_fields:
                update_fields.append("updated_at")
                locked.save(update_fields=update_fields)
            return locked
