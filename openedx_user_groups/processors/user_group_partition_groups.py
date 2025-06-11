"""
Outline processors for applying user group partition groups.
"""

from datetime import datetime
from typing import Dict, Set

from opaque_keys.edx.keys import CourseKey
from openedx.core import types
from openedx.core.djangoapps.content.learning_sequences.api.processors.base import OutlineProcessor
from xmodule.partitions.partitions import Group
from xmodule.partitions.partitions_service import get_user_partition_groups

from openedx_user_groups.partitions.user_group_partition_scheme import (
    USER_GROUP_PARTITION_ID,
    create_user_group_partition_with_course_id,
)
from openedx_user_groups.toggles import is_user_groups_enabled


class UserGroupPartitionGroupsOutlineProcessor(OutlineProcessor):
    """
    Processor for applying all user partition groups to the course outline.

    This processor is used to remove content from the course outline based on
    the user's user group membership. It is used in the courseware API to remove
    content from the course outline before it is returned to the client.
    """

    def __init__(self, course_key: CourseKey, user: types.User, at_time: datetime):
        """
        Initialize the UserGroupPartitionGroupsOutlineProcessor.

        Args:
            course_key (CourseKey): The course key.
            user (types.User): The user.
            at_time (datetime): The time at which the data is loaded.
        """
        super().__init__(course_key, user, at_time)
        self.user_groups: Dict[str, Group] = {}

    def load_data(self, _) -> None:
        """
        Pull user groups for this course and which group the user is in.
        """
        if not is_user_groups_enabled(self.course_key):
            return

        user_partition = create_user_group_partition_with_course_id(self.course_key)
        self.user_groups = get_user_partition_groups(
            self.course_key,
            [user_partition],
            self.user,
            partition_dict_key="id",
        ).get(USER_GROUP_PARTITION_ID)

    def _is_user_excluded_by_partition_group(self, user_partition_groups: Dict[int, Set[int]]):
        """
        Is the user part of the group to which the block is restricting content?

        Args:
            user_partition_groups (Dict[int, Set(int)]): Mapping from partition
                ID to the groups to which the user belongs in that partition.

        Returns:
            bool: True if the user is excluded from the content, False otherwise.
            The user is excluded from the content if and only if, for a non-empty
            partition group, the user is not in any of the groups for that partition.
        """
        if not is_user_groups_enabled(self.course_key):
            return False

        if not user_partition_groups:
            return False

        groups = user_partition_groups.get(USER_GROUP_PARTITION_ID)
        if not groups:
            return False

        for group in self.user_groups:
            if group.id in groups:
                return False

        return True

    def usage_keys_to_remove(self, full_course_outline):
        """
        Content group exclusions remove the content entirely.

        This method returns the usage keys of all content that should be
        removed from the course outline based on the user's user group membership.
        """
        removed_usage_keys = set()

        for section in full_course_outline.sections:
            remove_all_children = False

            if self._is_user_excluded_by_partition_group(section.user_partition_groups):
                removed_usage_keys.add(section.usage_key)
                remove_all_children = True

            for seq in section.sequences:
                if remove_all_children or self._is_user_excluded_by_partition_group(seq.user_partition_groups):
                    removed_usage_keys.add(seq.usage_key)

        return removed_usage_keys
