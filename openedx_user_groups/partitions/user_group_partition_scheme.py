"""
Provides a UserPartition driver for user groups.
"""

import logging

from django.utils.translation import gettext_lazy as _
from lms.djangoapps.courseware.masquerade import (
    get_course_masquerade,
    get_masquerading_user_group,
    is_masquerading_as_specific_student,
)

from xmodule.partitions.partitions import (
    Group,
    UserPartition, UserPartitionError
)


log = logging.getLogger(__name__)


USER_GROUP_PARTITION_ID = 1000000000
USER_GROUP_SCHEME = "user_group"
DUMMY_USER_GROUPS = [
    {
        "id": 1,
        "name": "User Group A",
        "description": "First group for testing",
    },
    {
        "id": 2,
        "name": "User Group B",
        "description": "Second group for testing",
    },
    {
        "id": 3,
        "name": "User Group C",
        "description": "Third group for testing",
    },
]

DUMMY_USER_GROUPS_MEMBERSHIP = {
    "admin": [2],
    "elon": [2, 3],
    "jeff": [1, 3],
    "marie": [1, 2, 3],
}


class UserGroupPartition(UserPartition):
    """
    Extends UserPartition to support dynamic groups pulled from the new user
    groups system.
    """

    @property
    def groups(self):
        """
        Dynamically generate groups (based on user groups) for this partition.
        """
        return [
            Group(user_group["id"], str(user_group["name"]))
            for user_group in DUMMY_USER_GROUPS
        ]


class UserGroupPartitionScheme:
    """Uses user groups to map learners into partition groups.

    - A user partition is created for each user group in the course with a
      unused partition ID generated in runtime by using generate_int_id() with
      min=MINIMUM_STATIC_PARTITION_ID and max=MYSQL_MAX_INT.
    - A (User) group is created for each user group in the course with the
      database user group ID as the group ID, and the user group name as the
      group name.
    - A user is assigned to a group if they are a member of the user group.
    """

    @classmethod
    def get_group_for_user(cls, course_key, user, user_partition):
        """Get the (User) Group from the specified user partition for the user.

        A user is assigned to the group via their user group membership and any
        mappings from user groups to partitions / groups that might exist.

        Args:
            course_key (CourseKey): The course key.
            user (User): The user.
            user_partition (UserPartition): The user partition.

        Returns:
            Group: The group in the specified user partition
        """
        # Un usuario podría pertenecer a multiples grupos. Este método asume que
        # el usuario pertenece a un solo grupo.
        if get_course_masquerade(
            user, course_key
        ) and not is_masquerading_as_specific_student(user, course_key):
            return get_masquerading_user_group(course_key, user, user_partition)

        user_groups_ids = DUMMY_USER_GROUPS_MEMBERSHIP[user.username]

        if not user_groups_ids:
            return None

        user_groups = []
        for user_group in DUMMY_USER_GROUPS:
            if user_group["id"] in user_groups_ids:
                user_groups.append(Group(user_group["id"], str(user_group["name"])))

        return user_groups

    @classmethod
    def create_user_partition(
        cls, id, name, description, groups=None, parameters=None, active=True
    ):  # pylint: disable=redefined-builtin, invalid-name
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


def create_user_group_partition_with_course_id(course_id):
    """
    Create and return the user group partition based only on course_id.
    If it cannot be created, None is returned.
    """
    try:
        user_group_scheme = UserPartition.get_scheme(USER_GROUP_SCHEME)
    except UserPartitionError:
        log.warning(
            f"No {USER_GROUP_SCHEME} scheme registered, UserGroupPartition will not be created."
        )
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
    Get the dynamic enrollment track user partition based on the user groups of the course.
    """
    return create_user_group_partition_with_course_id(course.id)
