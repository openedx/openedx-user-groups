"""Serializers for the openedx_user_groups app."""

from django.contrib.auth import get_user_model
from rest_framework import serializers

from openedx_user_groups.models import UserGroup

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):

    # TODO: Add more fields here, like is_staff, is_active, etc. profile?
    class Meta:
        model = User
        fields = ["username", "email", "first_name", "last_name"]


class ScopeSerializer(serializers.Serializer):
    """Serializer for scope - handles both input and output."""

    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField()
    description = serializers.CharField(required=False, allow_null=True)
    content_type = serializers.SerializerMethodField()
    content_object = serializers.DictField(write_only=True, required=False)

    def get_content_type(self, obj):
        """Get simplified content type information for output."""
        return {
            "object_id": obj.object_id,
            "content_type": str(obj.content_type),
        }


class CriterionSerializer(serializers.Serializer):
    """Serializer for criterion - handles both input and output."""

    criterion_type = serializers.CharField()
    criterion_operator = serializers.CharField()
    criterion_config = serializers.DictField()


class UserGroupSerializer(serializers.ModelSerializer):
    """Serializer for user group - handles both input and output."""

    scope = ScopeSerializer()
    criteria = CriterionSerializer(many=True, required=False)
    users = UserSerializer(many=True, read_only=True)
    evaluate_immediately = serializers.BooleanField(
        write_only=True, required=False, default=False
    )

    class Meta:
        model = UserGroup
        fields = [
            "id",
            "name",
            "description",
            "enabled",
            "scope",
            "last_membership_change",
            "criteria",
            "users",
            "evaluate_immediately",
        ]
