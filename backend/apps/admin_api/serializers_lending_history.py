from rest_framework import serializers


class LendingHistoryEntrySerializer(serializers.Serializer):
    username = serializers.CharField()
    issued_at = serializers.DateTimeField()
    quantity = serializers.IntegerField()


class LendingHistoryResponseSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    last_borrower = LendingHistoryEntrySerializer(allow_null=True)
    recent = LendingHistoryEntrySerializer(many=True)
