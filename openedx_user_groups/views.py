"""REST API to manage user groups, their criteria and membership."""

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.mixins import CreateModelMixin, ListModelMixin, RetrieveModelMixin
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from openedx_user_groups.api import (
    create_group_with_criteria,
    create_group_with_criteria_and_evaluate_membership,
    get_available_registered_criteria_schema,
    get_group_by_id,
)
from openedx_user_groups.models import UserGroup
from openedx_user_groups.serializers import UserGroupSerializer


class AvailableCriteriaView(APIView):
    """View to get all available criteria with their schema for fields, operators and descriptions."""

    def get(self, request):
        """Get all available criteria with their schema for fields, operators and descriptions."""
        criteria_data = get_available_registered_criteria_schema()
        return Response(criteria_data, status=status.HTTP_200_OK)


class UserGroupViewSet(
    ListModelMixin, RetrieveModelMixin, CreateModelMixin, GenericViewSet
):
    """ViewSet for user group operations using DRF mixins."""

    queryset = UserGroup.objects.all()
    serializer_class = UserGroupSerializer

    def create(self, request, *args, **kwargs):
        """Create a new user group with criteria."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        data = serializer.validated_data

        if data.get("evaluate_immediately", False):
            user_group = create_group_with_criteria_and_evaluate_membership(
                name=data["name"],
                description=data.get("description", ""),
                scope=data["scope"],
                criteria=data.get("criteria", []),
            )
        else:
            user_group = create_group_with_criteria(
                name=data["name"],
                description=data.get("description", ""),
                scope=data["scope"],
                criteria=data.get("criteria", []),
            )

        serializer = UserGroupSerializer(user_group)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, *args, **kwargs):
        """Get a specific user group by ID."""
        group_id = kwargs.get("pk")
        user_group = get_group_by_id(group_id)
        serializer = UserGroupSerializer(user_group)
        return Response(serializer.data, status=status.HTTP_200_OK)
