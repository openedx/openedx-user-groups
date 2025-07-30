"""This module is responsible for handling background tasks related to user groups opetations.

It is responsible for:
- Evaluate membership for a user group based on criteria
- Updating user groups when the criteria changes
- All operations that might be high impact and should be run in a background task
"""

from celery import shared_task

from openedx_user_groups.api import (
    evaluate_and_update_membership_for_group,
    evaluate_and_update_membership_for_multiple_groups,
)
from openedx_user_groups.criteria import BaseCriterionType
from openedx_user_groups.models import Criterion, UserGroup, UserGroupMembership


def orchestrate_user_groups_updates_based_on_events(
    event_type: str,
    event_data: dict,
    event_to_class_map: dict,
):
    """
    Orchestrate user groups updates for all groups that are affected by the event.

    This operation will be triggered by an event from the Open edX Events library which is associated
    with a sigle or multiple criteria types.

    This task will:
    1. Get all criteria types that are affected by the event
    2. Get all enabled groups that are configured with those criteria types
    3. Re-evaluate the membership for those groups if and only if:
        - The event usually represents the state of a single membership.
        - The membership state holds what was true at the time of the membership creation.
        - If the event data doesn't match the membership state, then the membership will be updated. Also groups of the
        same criteria type will be updated in case the user now belongs to another group.
    4. If there is no membership associated with the event, then all groups that are configured with the criteria
    types will be updated.
    """
    # Get the user from the event data
    user_id = event_data.get("id")  # TODO: is this always present?
    if not user_id:
        return

    # Get all criteria types affected by this event
    affected_criteria_types = event_to_class_map.get(event_type, [])
    if not affected_criteria_types:
        return

    # Get all memberships for this user in groups with affected criteria types
    memberships = (
        UserGroupMembership.objects.filter(
            user_id=user_id,
            is_active=True,
            group__enabled=True,
            group__criteria__criterion_type__in=affected_criteria_types,
        )
        .select_related("group")
        .prefetch_related("group__criteria")
        .distinct()  # Avoid duplicates if group has multiple affected criteria
    )

    # If there are no memberships for this user, then we should update all groups that are configured with the criteria types
    if not memberships:
        groups_to_update = UserGroup.objects.filter(
            enabled=True, criteria__criterion_type__in=affected_criteria_types
        ).values_list("id", flat=True)
        evaluate_and_update_membership_for_multiple_groups(list(groups_to_update))
        return

    groups_to_update = set()
    # Check existing memberships for state changes
    for membership in memberships:
        # Check if any of the group's criteria are affected and have state changes
        for criterion in membership.group.criteria.all():
            if criterion.criterion_type in affected_criteria_types:
                if check_if_membership_state_changed(
                    event_data, criterion.criterion_config
                ):
                    groups_to_update.add(membership.group.id)

    # Also check groups where the user is NOT a member but might now qualify
    # Get all groups with affected criteria types that the user is not currently in
    current_group_ids = [m.group.id for m in memberships]
    potential_groups = (
        UserGroup.objects.filter(
            enabled=True, criteria__criterion_type__in=affected_criteria_types
        )
        .exclude(id__in=current_group_ids)
        .distinct()
    )

    # Add these groups for evaluation as the user might now qualify
    groups_to_update.update(potential_groups.values_list("id", flat=True))

    # Update all affected groups
    if groups_to_update:
        evaluate_and_update_membership_for_multiple_groups(list(groups_to_update))


def check_if_membership_state_changed(event_data: dict, criterion_config: dict):
    """Check if the membership state has changed based on the event data.

    This function will check if the event data matches the criterion config.
    If the event data doesn't match the criterion config, then the membership state has changed.

    Args:
        event_data: The data from the event
        criterion_config: The configuration of the criterion

    Returns:
        bool: True if the membership state has changed, False otherwise
    """
    for key, value in criterion_config.items():
        if key not in event_data:
            return False
        if event_data[key] != value:
            return True
    return False
