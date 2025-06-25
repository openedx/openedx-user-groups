"""Interim module to define the events that trigger updates.

This module is used to define the events that trigger updates to the user groups.

This is a temporary module that will be replaced by the events defined in the openedx-events repository.
"""

import attr
from openedx_events.learning.data import UserData
from openedx_events.tooling import OpenEdxPublicSignal


@attr.s(frozen=True)
class UserDataExtended(UserData):
    is_staff = attr.ib(type=bool)


# .. event_type: org.openedx.learning.user.staff_status.changed.v1
# .. event_name: USER_STAFF_STATUS_CHANGED
# .. event_key_field: user.id
# .. event_description: Emitted when the user staff status changes.
# .. event_data: UserStaffStatusData
# .. event_trigger_repository: openedx/edx-platform
USER_STAFF_STATUS_CHANGED = OpenEdxPublicSignal(
    event_type="org.openedx.learning.user.staff_status.changed.v1",
    data={
        "user": UserDataExtended,
    },
)
