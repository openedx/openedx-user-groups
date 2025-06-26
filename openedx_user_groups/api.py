"""Module for the API of the user groups app.

Here we'll implement the API, evaluators and combinators. These components can be later moved to a service layer:

- The API (basic interfaces) will be used by other services to create and manage user groups.
- The evaluators will be used to evaluate the membership of a user group.
- The combinators will be used to combine the criteria of a user group to get the final membership.
"""

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models import Count
from django.utils import timezone

from openedx_user_groups.backends import DjangoORMBackendClient
from openedx_user_groups.criteria import BaseCriterionType
from openedx_user_groups.manager import CriterionManager, load_criterion_class_and_create_instance
from openedx_user_groups.models import Criterion, GroupCollection, Scope, UserGroup, UserGroupMembership
from openedx_user_groups.utils import process_content_object

User = get_user_model()


# Public API for User Group operations
__all__ = [
    "get_or_create_group_and_scope",
    "create_group_with_criteria",
    "create_group_with_criteria_and_evaluate_membership",
    "evaluate_and_update_membership_for_multiple_groups",
    "get_groups_for_scope",
    "get_group_by_id",
    "get_group_by_name_and_scope",
    "get_user_group_members",
    "update_group_name_or_description",
    "soft_delete_group",
    "hard_delete_group",
    "get_groups_for_user",
    "create_group_collection_and_add_groups",
    "evaluate_and_update_membership_for_group_collection",
]


def get_or_create_group_and_scope(
    name: str, description: str, scope: dict
) -> tuple[UserGroup, Scope]:
    """Get or create a user group and its scope.

    Args:
        name (str): The name of the user group.
        description (str): A brief description of the user group.
        scope (dict): The context of the scope.

    Returns:
        tuple: A tuple containing the user group and scope.
    """
    with transaction.atomic():
        content_object = scope.get("content_object", {})

        content_type, object_id = process_content_object(content_object)

        scope_obj, created = Scope.objects.get_or_create(
            name=scope["name"],
            description=scope.get("description", ""),
            content_type=content_type,
            object_id=object_id,
        )

        user_group, _ = UserGroup.objects.get_or_create(
            name=name,
            description=description,
            scope=scope_obj,
        )
    return user_group, scope_obj


def create_group_with_criteria_from_data(
    name: str,
    description: str,
    scope: dict,
    criteria: [dict],  # TODO: should we use pydantic models instead of dicts?
):
    """Create a new user group with the given name, description, scope, and criteria.
    This criteria hasn't been instantiated and validated yet.

    Args:
        name (str): The name of the user group.
        description (str): A brief description of the user group.
        scope (dict): The context of the scope.
        criteria (list): A list of criterion data.

    Returns:
        UserGroup: The created user group.
    """
    with transaction.atomic():
        user_group, scope = get_or_create_group_and_scope(name, description, scope)
        for data in criteria:
            criterion_instance = load_criterion_class_and_create_instance(
                data["criterion_type"],
                data["criterion_operator"],
                data["criterion_config"],
                scope,
                DjangoORMBackendClient,
            )
            criterion = Criterion.objects.create(
                user_group=user_group, **criterion_instance.serialize()
            )

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
            result = criterion.criterion_instance.evaluate()

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
    name: str, description: str, scope: dict, criteria: [dict]
):
    """Create a new user group with the given name, description, scope, and criteria.
    This criteria have been instantiated and validated.

    Args:
        name (str): The name of the user group.
        description (str): A brief description of the user group.
        scope (dict): The context of the scope.
        criteria (list): A list of criterion data following the format of:
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
            name, description, scope, criteria
        )
        evaluate_and_update_membership_for_group(user_group.id)
    return user_group


def create_group_with_criteria(
    name: str, description: str, scope: dict, criteria: [dict]
):
    """Create a new user group with the given name, description, scope, and criteria.
    This criteria hasn't been instantiated and validated yet.

    Args:
        name (str): The name of the user group.
        description (str): A brief description of the user group.
        scope (dict): The context of the scope.
        criteria (list): A list of criterion data following the format of:
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
            name, description, scope, criteria
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


def get_group_by_id(group_id: int):
    """Get a user group by its ID.

    Args:
        group_id (int): The ID of the user group.

    Returns:
        UserGroup: The user group.
    """
    return (
        UserGroup.objects.select_related("scope")
        .prefetch_related("criteria")
        .get(id=group_id)
    )


def create_group_collection_and_add_groups(
    name: str, description: str, group_ids: [int]
):
    """Create a new group collection and add groups to it.

    Args:
        name (str): The name of the group collection.
        description (str): A brief description of the group collection.
        group_ids (list): The IDs of the user groups to add to the collection.

    Returns:
        GroupCollection: The created group collection.
    """
    with transaction.atomic():
        group_collection = GroupCollection.objects.create(
            name=name, description=description
        )
        for group_id in group_ids:
            group = get_group_by_id(group_id)
            group_collection.user_groups.add(group)

    return group_collection


def get_group_collection_by_id(group_collection_id: int):
    """Get a group collection by its ID.

    Args:
        group_collection_id (int): The ID of the group collection.

    Returns:
        GroupCollection: The group collection.
    """
    return GroupCollection.objects.prefetch_related("user_groups").get(
        id=group_collection_id
    )


def evaluate_and_update_membership_for_group_collection(group_collection_id: int):
    """Evaluate the membership of a group collection and update the membership records.

    This method considers the mutual exclusivity of the groups in the collection.

    Args:
        group_collection_id (int): The ID of the group collection.

    Returns:
        tuple:
        - GroupCollection: The group collection.
        - QuerySet: The duplicates users found and removed from the group collection.
    """
    with transaction.atomic():
        group_collection = get_group_collection_by_id(group_collection_id)
        for group in group_collection.user_groups.all():
            evaluate_and_update_membership_for_group(group.id)
        # Find duplicates in the group collection to remove them and prompt for action
        duplicates = (
            User.objects.filter(
                usergroupmembership__group__in=group_collection.user_groups.all()
            )
            .annotate(group_count=Count("usergroupmembership__group", distinct=True))
            .filter(group_count__gt=1)
        )
        if duplicates.exists():
            # TODO: Prompt for action, but for the time being remove the duplicates
            for duplicate in duplicates:
                duplicate.usergroupmembership_set.filter(
                    group__in=group_collection.user_groups.all()
                ).delete()
        return group_collection, duplicates


def get_available_registered_criteria_schema():
    """Get all available with their schema for fields, operators and descriptions.

    Returns:
        dict: A dictionary containing the schema for all available criteria. For example:
        {
            "criterion_type": {
                "fields": {
                    "field_name": {
                        "type": "string",
                        "description": "Description of the field"
                    }
                },
                "operators": ["operator1", "operator2"],
                "description": "Description of the criterion",
                "criterion_type": "criterion_type",
                "supported_scopes": ["course", "organization", "instance"]
            }
        }
    """
    return {
        criterion_type: criterion_class.get_schema()
        for criterion_type, criterion_class in CriterionManager.get_criterion_classes().items()
    }


# TODO: THESE METHODS I HAVEN'T TESTED YET


def get_group_by_name_and_scope(name: str, scope: str):
    """Get a user group by its name and scope.

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
