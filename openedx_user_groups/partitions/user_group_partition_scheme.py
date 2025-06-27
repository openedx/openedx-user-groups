"""
Provides a UserPartition driver for user groups.
"""

import logging
from unittest.mock import Mock

from django.utils.translation import gettext_lazy as _

try:
    from lms.djangoapps.courseware.masquerade import (
        get_course_masquerade,
        get_masquerading_user_group,
        is_masquerading_as_specific_student,
    )
    from openedx.core import types
    from xmodule.partitions.partitions import Group, UserPartition, UserPartitionError
except ImportError:
    get_course_masquerade = Mock()
    get_masquerading_user_group = Mock()
    is_masquerading_as_specific_student = Mock()
    types = Mock()
    Group = Mock()

    class UserPartitionError(Exception):
        """Mock UserPartitionError class for testing."""

    class UserPartition:
        """Mock UserPartition class for testing."""

        # pylint: disable=redefined-builtin, too-many-positional-arguments, unused-argument
        def __init__(self, id, name, description, groups, scheme, parameters, active=True):
            self.parameters = parameters
            self.scheme = scheme
            self.id = id
            self.name = name
            self.description = description
            self.active = active

        @property
        def groups(self):
            return self.groups


from opaque_keys.edx.keys import CourseKey

from openedx_user_groups.models import UserGroup, UserGroupMembership
from openedx_user_groups.toggles import is_user_groups_enabled

log = logging.getLogger(__name__)

# TODO: This is a temporary ID. We should use a more permanent ID.
USER_GROUP_PARTITION_ID = 1000000000
USER_GROUP_SCHEME = "user_group"


class UserGroupPartition(UserPartition):
    """
    Extends UserPartition to support dynamic groups pulled from the new user
    groups system.
    """

    @property
    def groups(self) -> list[Group]:
        """
        Dynamically generate groups (based on user groups) for this partition.
        """
        course_key = CourseKey.from_string(self.parameters["course_id"])
        if not is_user_groups_enabled(course_key):
            return []

        # TODO: Only get user groups for the course.
        user_groups = UserGroup.objects.filter(enabled=True)
        return [Group(user_group.id, str(user_group.name)) for user_group in user_groups]


class UserGroupPartitionScheme:
    """Uses user groups to map learners into partition groups.

    This scheme is only available if the ENABLE_USER_GROUPS waffle flag is enabled for the course.

    This is how it works:
    - A only one user partition is created for each course with the `USER_GROUP_PARTITION_ID`.
    - A (Content) group is created for each user group in the course with the
      database user group ID as the group ID, and the user group name as the
      group name.
    - A user is assigned to a group if they are a member of the user group.
    """

    @classmethod
    def get_group_for_user(
        cls, course_key: CourseKey, user: types.User, user_partition: UserPartition
    ) -> list[Group] | None:
        """Get the (User) Group from the specified user partition for the user.

        A user is assigned to the group via their user group membership and any
        mappings from user groups to partitions / groups that might exist.

        Args:
            course_key (CourseKey): The course key.
            user (types.User): The user.
            user_partition (UserPartition): The user partition.

        Returns:
            List[Group]: The groups in the specified user partition for the user.
                None if the user is not a member of any group.
        """
        if not is_user_groups_enabled(course_key):
            return None

        # TODO: A user could belong to multiple groups. This method assumes that
        # the user belongs to a single group. This should be renamed?
        if get_course_masquerade(user, course_key) and not is_masquerading_as_specific_student(user, course_key):
            return get_masquerading_user_group(course_key, user, user_partition)

        user_group_ids = UserGroupMembership.objects.filter(user=user, is_active=True).values_list(
            "group__id", flat=True
        )
        all_user_groups: list[UserGroup] = UserGroup.objects.filter(enabled=True)

        if not user_group_ids:
            return None

        user_groups = []
        for user_group in all_user_groups:
            if user_group.id in user_group_ids:
                user_groups.append(Group(user_group.id, str(user_group.name)))

        return user_groups

    # pylint: disable=redefined-builtin, invalid-name, too-many-positional-arguments
    @classmethod
    def create_user_partition(
        cls,
        id: int,
        name: str,
        description: str,
        groups: list[Group] | None = None,
        parameters: dict | None = None,
        active: bool = True,
    ) -> UserPartition:
        """Create a custom UserPartition to support dynamic groups based on user groups.

        A Partition has an id, name, scheme, description, parameters, and a
        list of groups. The id is intended to be unique within the context where
        these are used. (e.g., for partitions of users within a course, the ids
        should be unique per-course).

        The scheme is used to assign users into groups. The parameters field is
        used to save extra parameters e.g., location of the course ID for this
        partition scheme.

        Partitions can be marked as inactive by setting the "active" flag to False.
        Any group access rule referencing inactive partitions will be ignored
        when performing access checks.

        Args:
            id (int): The id of the partition.
            name (str): The name of the partition.
            description (str): The description of the partition.
            groups (list of Group): The groups in the partition.
            parameters (dict): The parameters for the partition.
            active (bool): Whether the partition is active.

        Returns:
            UserGroupPartition: The user partition.
        """
        course_key = CourseKey.from_string(parameters["course_id"])
        if not is_user_groups_enabled(course_key):
            return None

        user_group_partition = UserGroupPartition(
            id,
            str(name),
            str(description),
            groups,
            cls,
            parameters,
            active=active,
        )

        return user_group_partition


def create_user_group_partition_with_course_id(course_id: CourseKey) -> UserPartition | None:
    """
    Create and return the user group partition based only on course_id.
    If it cannot be created, None is returned.
    """
    try:
        user_group_scheme = UserPartition.get_scheme(USER_GROUP_SCHEME)
    except UserPartitionError:
        log.warning(f"No {USER_GROUP_SCHEME} scheme registered, UserGroupPartition will not be created.")
        return None

    partition = user_group_scheme.create_user_partition(
        id=USER_GROUP_PARTITION_ID,
        name=_("User Groups"),
        description=_("Partition for segmenting users by user groups"),
        parameters={"course_id": str(course_id)},
    )

    return partition


def create_user_group_partition(course):
    """
    Get the dynamic user group user partition based on the user groups of the course.
    """
    if not is_user_groups_enabled(course.id):
        return []

    return create_user_group_partition_with_course_id(course.id)
