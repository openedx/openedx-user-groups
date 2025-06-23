"""This module is responsible for handling event-based updates to user groups.

It is responsible for:
- Adding users to user groups when they meet the criteria
- Removing users from user groups when they no longer meet the criteria
- Updating user groups when the criteria changes
"""

import attr

from openedx_user_groups.criteria import BaseCriterionType
from openedx_user_groups.tasks import orchestrate_user_groups_updates_based_on_events


def handle_user_group_update(sender, signal, **kwargs):
    """Handler for all events related to user-groups criteria.

    This handler listens to all events configured within each criterion type and orchestrates the necessary updates to the user groups.

    Args:
        sender: The sender of the signal.
        signal: The signal that was sent.
        **kwargs: Additional keyword arguments.
    """
    orchestrate_user_groups_updates_based_on_events(
        signal.event_type,
        attr.asdict(kwargs.get("user")),
        BaseCriterionType._event_to_class_map,  # TODO: this is very specific for the new USER_STAFF_STATUS_CHANGED event and user-related events
    )
