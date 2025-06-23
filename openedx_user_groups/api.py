"""Module for the API of the user groups app.

Here we'll implement the API, evaluators and combinators. These components can be later moved to a service layer:

- The API (basic interfaces) will be used by other services to create and manage user groups.
- The evaluators will be used to evaluate the membership of a user group.
- The combinators will be used to combine the criteria of a user group to get the final membership.
"""

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from openedx_user_groups.backends import DjangoORMBackendClient
from openedx_user_groups.criteria import BaseCriterionType
from openedx_user_groups.manager import load_criterion_class
from openedx_user_groups.models import Criterion, Scope, UserGroup, UserGroupMembership

User = get_user_model()


# Public API for User Group operations
__all__ = [
    "get_or_create_group_and_scope",
    "create_group_with_criteria",
    "create_group_with_criteria_and_evaluate_membership",
    "evaluate_and_update_membership_for_multiple_groups",
    "get_groups_for_scope",
    "get_group_by_id",
    "get_group_by_name",
    "get_group_by_name_and_scope",
    "get_user_group_members",
    "update_group_name_or_description",
    "soft_delete_group",
    "hard_delete_group",
    "get_groups_for_user",
]


def get_scope_type_from_content_type(content_type):
    """
    Map Django ContentType to scope type names used by criteria.

    Args:
        content_type: Django ContentType instance

    Returns:
        str: Scope type name (e.g., "course", "organization", "instance")
    """
    # Mapping from Django model names to scope types
    model_to_scope_mapping = {
        "course": "course",  # When we have actual course models
        "courseoverview": "course",  # edx-platform course overview model
        "organization": "organization",  # Organization models
    }

    model_name = content_type.model
    return model_to_scope_mapping.get(model_name, "instance")  # Default to instance


def get_or_create_group_and_scope(
    name: str, description: str, scope_context: dict
) -> tuple[UserGroup, Scope]:
    """Create a new user group with the given name, description, and scope. No criteria is associated with the group.

    Args:
        name (str): The name of the user group.
        description (str): A brief description of the user group.
        scope (Scope): The scope of the user group.

    Returns:
        UserGroup: The created user group.
    """
    with transaction.atomic():
        scope, created = Scope.objects.get_or_create(
            name=scope_context[
                "name"
            ],  # TODO: what is this going to be? The course_key (CourseKey) as string?
            content_type=scope_context["content_object"]["content_type"],
            object_id=scope_context["content_object"]["object_id"],
        )
        user_group, _ = UserGroup.objects.get_or_create(
            name=name,
            description=description,
            scope=scope,
        )
    return user_group, scope


def load_criterion_class_and_create_instance(
    criterion_type: str, criterion_operator: str, criterion_config: dict
):
    """Create a new criterion class.

    Args:
        criterion_type (str): The type of the criterion.
        criterion_operator (str): The operator of the criterion.
        criterion_config (dict): The configuration of the criterion.

    Returns:
        BaseCriterionType: The created criterion class.
    """
    criterion_class = load_criterion_class(criterion_type)
    criterion_instance = criterion_class(criterion_operator, criterion_config)
    return criterion_instance


def create_group_with_criteria_from_data(
    name: str, description: str, scope_context: dict, criterion_data: [dict]  # TODO: should we use pydantic models instead of dicts?
):
    """Create a new user group with the given name, description, scope, and criteria.
    This criteria hasn't been instantiated and validated yet.

    Args:
        name (str): The name of the user group.
        description (str): A brief description of the user group.
        scope_context (dict): The context of the scope.
        criterion_data (list): A list of criterion data.

    Returns:
        UserGroup: The created user group.
    """
    with transaction.atomic():
        user_group, scope = get_or_create_group_and_scope(
            name, description, scope_context
        )
        for data in criterion_data:
            criterion_instance = load_criterion_class_and_create_instance(
                data["criterion_type"],
                data["criterion_operator"],
                data["criterion_config"],
            )
            scope_type = get_scope_type_from_content_type(scope.content_type)
            assert scope_type in criterion_instance.scopes, f"Criterion '{criterion_instance.criterion_type}' does not support scope type '{scope_type}'. Supported scopes: {criterion_instance.scopes}"
            Criterion.objects.create(user_group=user_group, **criterion_instance.serialize())
    return user_group


def evaluate_and_update_membership_for_group(group_id: int):
    """Evaluate the membership of a user group based on the criteria and update the membership records.

    Args:
        group_id (str): The ID of the user group.
    """
    # TODO: We should enforce that this is done asynchronously.
    with transaction.atomic():
        user_group = get_group_by_id(group_id)
        # Evaluatate criteria and build list of Q objects - Done by what we called "combinator"
        criteria_results = []
        for criterion in user_group.criteria.all():
            result = criterion.criterion_instance.evaluate(
                current_scope=user_group.scope,
                backend_client=DjangoORMBackendClient,  # TODO: for now we'd only support DjangoORMBackendClient. But I think we could pass a list of registered backend clients here.
            )

            criteria_results.append(result)

        # This is the reducer / accumulator part. - Done by what we called "evaluator engine"
        # Combine the results using intersection (AND logic) for multiple criteria for single criteria we could just use the first result.
        # TODO: For simplicity we're only considering AND logic for now. When considering OR logic we would need a logic tree for combining the results correctly.
        if criteria_results:
            # Start with the first QuerySet and intersect with subsequent ones
            users = criteria_results[0]
            for result in criteria_results[1:]:
                users = users.intersection(
                    result
                )  # TODO: is it better to use Q objects instead of QuerySets?
        else:
            # No criteria, return empty queryset
            users = User.objects.none()

        # Update membership records - This should be done by the User Group service
        # Simple membership update: clear existing and create new ones with basic metadata
        user_group.usergroupmembership_set.all().delete()

        # Create new memberships
        new_memberships = [
            UserGroupMembership(
                user=user,
                group=user_group,
                joined_at=timezone.now(),
            )
            for user in users
        ]
        UserGroupMembership.objects.bulk_create(new_memberships)

        # Update last membership change timestamp
        user_group.last_membership_change = timezone.now()
        user_group.save(update_fields=["last_membership_change"])


def evaluate_and_update_membership_for_multiple_groups(group_ids: [int]):
    """Evaluate the membership of a list of user groups based on the criteria and update the membership records.

    Args:
        group_ids (list): The IDs of the user groups.
    """
    with transaction.atomic():
        for group_id in group_ids:
            evaluate_and_update_membership_for_group(group_id)


def create_group_with_criteria_and_evaluate_membership(
    name: str, description: str, scope_context: dict, criterion_data: dict
):
    """Create a new user group with the given name, description, scope, and criterion.
    This criterion has been instantiated and validated.

    Args:
        name (str): The name of the user group.
        description (str): A brief description of the user group.
        scope_context (dict): The context of the scope.
        criterion_data (dict): The data of the criterion following the format of:
            {
                "criterion_type": str,
                "criterion_operator": str,
                "criterion_config": dict,
            }

    Returns:
        UserGroup: The created user group.
    """
    with transaction.atomic():
        user_group = create_group_with_criteria_from_data(
            name, description, scope_context, criterion_data
        )
        evaluate_and_update_membership_for_group(user_group.id)
    return user_group


def create_group_with_criteria(
    name: str, description: str, scope_context: dict, criterion_data: [dict]
):
    """Create a new user group with the given name, description, scope, and criteria.
    This criteria hasn't been instantiated and validated yet.

    Args:
        name (str): The name of the user group.
        description (str): A brief description of the user group.
        scope_context (dict): The context of the scope.
        criterion_data (list): A list of criterion data following the format of:
            {
                "criterion_type": str,
                "criterion_operator": str,
                "criterion_config": dict,
            }

    Returns:
        UserGroup: The created user group.
    """
    with transaction.atomic():
        user_group = create_group_with_criteria_from_data(
            name, description, scope_context, criterion_data
        )
    return user_group


def get_groups_for_scope(content_object_id: int):
    """Get all user groups for a given scope.

    Args:
        content_object_id (int): The ID of the content object. The idea would be to pass the ID of the course,
        organization, or instance.

    Returns:
        list: A list of user groups with minimum information.
    """
    return Scope.objects.get(content_object_id=content_object_id).user_groups.all()


def get_groups_for_user(user_id: int):
    """Get all user groups for a given user.

    This method is used to get all user groups for a given user.
    It is used to check if the user is a member of any group.

    Args:
        user_id (int): The ID of the user.

    Returns:
        list: A list of user groups with minimum information.
    """
    return UserGroupMembership.objects.filter(
        user_id=user_id, is_active=True
    ).select_related("group")


# TODO: THESE METHODS I HAVEN'T TESTED YET


def get_group_by_id(group_id: int):
    """Get a user group by its ID.

    Args:
        group_id (int): The ID of the user group.

    Returns:
        UserGroup: The user group.
    """
    return UserGroup.objects.get(id=group_id)


def get_group_by_name(name: str):
    """Get a user group by its name.

    Args:
        name (str): The name of the user group.

    Returns:
        UserGroup: The user group.
    """
    return UserGroup.objects.get(name=name)


def get_group_by_name_and_scope(name: str, scope: str):
    """Get a user group by its name and scope. TODO: should we allow multiple groups with the same name but different scopes?

    Args:
        name (str): The name of the user group.
        scope (str): The scope of the user group.

    Returns:
        UserGroup: The user group.
    """
    return UserGroup.objects.get(name=name, scope=scope)


def get_user_group_members(group_id: int):
    """Get the members of a user group.

    Args:
        group_id (int): The ID of the user group.

    Returns:
        list: A list of users that are members of the user group.
    """
    return UserGroup.objects.get(id=group_id).users.all()


def update_group_name_or_description(group_id: int, name: str, description: str):
    """Update the name or description of a user group.

    Args:
        group_id (str): The ID of the user group.
        name (str): The name of the user group.
        description (str): A brief description of the user group.
    """
    UserGroup.objects.filter(id=group_id).update(name=name, description=description)


def hard_delete_group(group_id: int):
    """Hard delete a user group. This will delete the group and all its criteria."""
    UserGroup.objects.filter(id=group_id).delete()


def soft_delete_group(group_id: int):
    """Soft delete a user group. This will not delete the group, but it will prevent it from being used by disabling it."""
    UserGroup.objects.filter(id=group_id).update(is_active=False)


def enable_group(group_id: int):
    """Enable a user group. This will allow it to be used again."""
    UserGroup.objects.filter(id=group_id).update(is_active=True)


def disable_group(group_id: int):
    """Disable a user group. This will prevent it from being used."""
    UserGroup.objects.filter(id=group_id).update(is_active=False)
