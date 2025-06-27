"""
Unit tests for UserGroupPartitionGroupsOutlineProcessor.

This test suite covers all methods and behaviors of the UserGroupPartitionGroupsOutlineProcessor
class, including initialization, data loading, partition group exclusion logic, and usage key removal.
"""

from datetime import datetime
from unittest.mock import Mock, patch

from django.test import TestCase
from opaque_keys.edx.keys import CourseKey

from openedx_user_groups.processors.user_group_partition_groups import (
    USER_GROUP_PARTITION_ID,
    UserGroupPartitionGroupsOutlineProcessor,
)
from tests.factories import UserFactory


class GroupMock:
    """Mock class for course outline sections."""

    def __init__(self, id, name):  # pylint: disable=redefined-builtin
        self.id = id
        self.name = name

    def __eq__(self, other):
        """Compare GroupMock instances by their attributes."""
        if not isinstance(other, GroupMock):
            return False
        return self.id == other.id and self.name == other.name


class MockOutlineSection:
    """Mock class for course outline sections."""

    def __init__(self, usage_key, user_partition_groups=None):
        self.usage_key = usage_key
        self.user_partition_groups = user_partition_groups or {}
        self.sequences = []


class MockOutlineSequence:
    """Mock class for course outline sequences."""

    def __init__(self, usage_key, user_partition_groups=None):
        self.usage_key = usage_key
        self.user_partition_groups = user_partition_groups or {}


class MockFullCourseOutline:
    """Mock class for full course outline."""

    def __init__(self, sections=None):
        self.sections = sections or []


# pylint: disable=protected-access
class TestUserGroupPartitionGroupsOutlineProcessor(TestCase):
    """Test suite for UserGroupPartitionGroupsOutlineProcessor."""

    def setUp(self):
        """Set up test data."""
        self.course_key = CourseKey.from_string("course-v1:edX+Demo+Course")
        self.user = UserFactory()
        self.at_time = datetime.now()
        self.user_group_1 = GroupMock(id=1, name="Test Group 1")
        self.user_group_2 = GroupMock(id=2, name="Test Group 2")

    @patch("openedx_user_groups.processors.user_group_partition_groups.is_user_groups_enabled")
    def test_initialization(self, mock_is_enabled: Mock):
        """Test processor initialization."""
        mock_is_enabled.return_value = True

        processor = UserGroupPartitionGroupsOutlineProcessor(self.course_key, self.user, self.at_time)

        self.assertEqual(processor.course_key, self.course_key)
        self.assertEqual(processor.user, self.user)
        self.assertEqual(processor.at_time, self.at_time)
        self.assertEqual(processor.user_groups, [])

    @patch("openedx_user_groups.processors.user_group_partition_groups.create_user_group_partition_with_course_id")
    @patch("openedx_user_groups.processors.user_group_partition_groups.get_user_partition_groups")
    @patch("openedx_user_groups.processors.user_group_partition_groups.is_user_groups_enabled")
    def test_load_data_when_user_groups_enabled(
        self, mock_is_enabled: Mock, mock_get_groups: Mock, mock_create_partition: Mock
    ):
        """Test load_data method when user groups are enabled."""
        mock_is_enabled.return_value = True
        # Mock partition and groups
        mock_partition = Mock()
        mock_create_partition.return_value = mock_partition
        mock_group_1 = GroupMock(id=1, name="Test Group 1")
        mock_group_2 = GroupMock(id=2, name="Test Group 2")
        mock_get_groups.return_value = {USER_GROUP_PARTITION_ID: {1: mock_group_1, 2: mock_group_2}}

        processor = UserGroupPartitionGroupsOutlineProcessor(self.course_key, self.user, self.at_time)
        processor.load_data(None)

        mock_create_partition.assert_called_once_with(self.course_key)
        mock_get_groups.assert_called_once_with(self.course_key, [mock_partition], self.user, partition_dict_key="id")
        self.assertEqual(len(processor.user_groups), 2)
        self.assertIn(1, processor.user_groups)
        self.assertIn(2, processor.user_groups)

    @patch("openedx_user_groups.processors.user_group_partition_groups.is_user_groups_enabled")
    def test_load_data_when_user_groups_disabled(self, mock_is_enabled: Mock):
        """Test load_data method when user groups are disabled."""
        mock_is_enabled.return_value = False

        processor = UserGroupPartitionGroupsOutlineProcessor(self.course_key, self.user, self.at_time)
        processor.load_data(None)

        self.assertEqual(processor.user_groups, [])

    @patch("openedx_user_groups.processors.user_group_partition_groups.create_user_group_partition_with_course_id")
    @patch("openedx_user_groups.processors.user_group_partition_groups.get_user_partition_groups")
    @patch("openedx_user_groups.processors.user_group_partition_groups.is_user_groups_enabled")
    def test_load_data_when_no_user_groups_found(
        self, mock_is_enabled: Mock, mock_get_groups: Mock, mock_create_partition: Mock
    ):
        """Test load_data method when no user groups are found."""
        mock_is_enabled.return_value = True
        mock_partition = Mock()
        mock_create_partition.return_value = mock_partition
        mock_get_groups.return_value = {}

        processor = UserGroupPartitionGroupsOutlineProcessor(self.course_key, self.user, self.at_time)
        processor.load_data(None)

        self.assertIsNone(processor.user_groups)

    @patch("openedx_user_groups.processors.user_group_partition_groups.is_user_groups_enabled")
    def test_is_user_excluded_by_partition_group_when_disabled(self, mock_is_enabled: Mock):
        """Test _is_user_excluded_by_partition_group when user groups are disabled."""
        mock_is_enabled.return_value = False

        processor = UserGroupPartitionGroupsOutlineProcessor(self.course_key, self.user, self.at_time)
        result = processor._is_user_excluded_by_partition_group({1: {1, 2}})

        self.assertFalse(result)

    @patch("openedx_user_groups.processors.user_group_partition_groups.is_user_groups_enabled")
    def test_is_user_excluded_by_partition_group_when_no_partition_groups(self, mock_is_enabled: Mock):
        """Test _is_user_excluded_by_partition_group when no partition groups are provided."""
        mock_is_enabled.return_value = True

        processor = UserGroupPartitionGroupsOutlineProcessor(self.course_key, self.user, self.at_time)
        result = processor._is_user_excluded_by_partition_group({})

        self.assertFalse(result)

    @patch("openedx_user_groups.processors.user_group_partition_groups.is_user_groups_enabled")
    def test_is_user_excluded_by_partition_group_when_no_user_group_partition(self, mock_is_enabled: Mock):
        """Test _is_user_excluded_by_partition_group when no user group partition is found."""
        mock_is_enabled.return_value = True

        processor = UserGroupPartitionGroupsOutlineProcessor(self.course_key, self.user, self.at_time)
        result = processor._is_user_excluded_by_partition_group({999: {1, 2}})

        self.assertFalse(result)

    @patch("openedx_user_groups.processors.user_group_partition_groups.is_user_groups_enabled")
    def test_is_user_excluded_by_partition_group_when_user_in_group(self, mock_is_enabled: Mock):
        """Test _is_user_excluded_by_partition_group when user is in one of the groups."""
        mock_is_enabled.return_value = True

        processor = UserGroupPartitionGroupsOutlineProcessor(self.course_key, self.user, self.at_time)
        processor.user_groups = [self.user_group_1, self.user_group_2]
        result = processor._is_user_excluded_by_partition_group({USER_GROUP_PARTITION_ID: {1, 3}})

        self.assertFalse(result)

    @patch("openedx_user_groups.processors.user_group_partition_groups.is_user_groups_enabled")
    def test_is_user_excluded_by_partition_group_when_user_not_in_group(self, mock_is_enabled: Mock):
        """Test _is_user_excluded_by_partition_group when user is not in any of the groups."""
        mock_is_enabled.return_value = True

        processor = UserGroupPartitionGroupsOutlineProcessor(self.course_key, self.user, self.at_time)
        processor.user_groups = [self.user_group_1, self.user_group_2]
        result = processor._is_user_excluded_by_partition_group({USER_GROUP_PARTITION_ID: {3, 4}})

        self.assertTrue(result)

    @patch("openedx_user_groups.processors.user_group_partition_groups.is_user_groups_enabled")
    def test_usage_keys_to_remove_with_no_exclusions(self, mock_is_enabled: Mock):
        """Test usage_keys_to_remove when no content should be excluded."""
        mock_is_enabled.return_value = True
        # Create mock outline with sections and sequences
        section1 = MockOutlineSection("section1", {})
        section1.sequences = [MockOutlineSequence("seq1", {}), MockOutlineSequence("seq2", {})]
        section2 = MockOutlineSection("section2", {})
        section2.sequences = [MockOutlineSequence("seq3", {})]
        full_course_outline = MockFullCourseOutline([section1, section2])

        processor = UserGroupPartitionGroupsOutlineProcessor(self.course_key, self.user, self.at_time)
        result = processor.usage_keys_to_remove(full_course_outline)

        self.assertEqual(result, set())

    @patch("openedx_user_groups.processors.user_group_partition_groups.is_user_groups_enabled")
    def test_usage_keys_to_remove_with_section_exclusion(self, mock_is_enabled: Mock):
        """Test usage_keys_to_remove when a section should be excluded."""
        mock_is_enabled.return_value = True
        # Create mock outline with one excluded section
        section1 = MockOutlineSection(
            "section1",
            {USER_GROUP_PARTITION_ID: {3, 4}},  # User not in these groups
        )
        section1.sequences = [MockOutlineSequence("seq1", {}), MockOutlineSequence("seq2", {})]
        section2 = MockOutlineSection("section2", {})
        section2.sequences = [MockOutlineSequence("seq3", {})]
        full_course_outline = MockFullCourseOutline([section1, section2])

        processor = UserGroupPartitionGroupsOutlineProcessor(self.course_key, self.user, self.at_time)
        processor.user_groups = [self.user_group_1, self.user_group_2]
        result = processor.usage_keys_to_remove(full_course_outline)

        expected = {"section1", "seq1", "seq2"}
        self.assertEqual(result, expected)

    @patch("openedx_user_groups.processors.user_group_partition_groups.is_user_groups_enabled")
    def test_usage_keys_to_remove_with_sequence_exclusion(self, mock_is_enabled: Mock):
        """Test usage_keys_to_remove when a sequence should be excluded."""
        mock_is_enabled.return_value = True
        # Create mock outline with one excluded sequence
        section1 = MockOutlineSection("section1", {})
        section1.sequences = [
            MockOutlineSequence(
                "seq1",
                {USER_GROUP_PARTITION_ID: {3, 4}},  # User not in these groups
            ),
            MockOutlineSequence("seq2", {}),
        ]
        section2 = MockOutlineSection("section2", {})
        section2.sequences = [MockOutlineSequence("seq3", {})]
        full_course_outline = MockFullCourseOutline([section1, section2])

        processor = UserGroupPartitionGroupsOutlineProcessor(self.course_key, self.user, self.at_time)
        processor.user_groups = [self.user_group_1, self.user_group_2]
        result = processor.usage_keys_to_remove(full_course_outline)

        expected = {"seq1"}
        self.assertEqual(result, expected)

    @patch("openedx_user_groups.processors.user_group_partition_groups.is_user_groups_enabled")
    def test_usage_keys_to_remove_with_multiple_exclusions(self, mock_is_enabled: Mock):
        """Test usage_keys_to_remove with multiple exclusions."""
        mock_is_enabled.return_value = True
        # Create mock outline with multiple exclusions
        section1 = MockOutlineSection(
            "section1",
            {USER_GROUP_PARTITION_ID: {3, 4}},  # User not in these groups
        )
        section1.sequences = [MockOutlineSequence("seq1", {}), MockOutlineSequence("seq2", {})]
        section2 = MockOutlineSection("section2", {})
        section2.sequences = [
            MockOutlineSequence(
                "seq3",
                {USER_GROUP_PARTITION_ID: {5, 6}},  # User not in these groups
            ),
            MockOutlineSequence("seq4", {}),
        ]
        full_course_outline = MockFullCourseOutline([section1, section2])

        processor = UserGroupPartitionGroupsOutlineProcessor(self.course_key, self.user, self.at_time)
        processor.user_groups = [self.user_group_1, self.user_group_2]
        result = processor.usage_keys_to_remove(full_course_outline)

        expected = {"section1", "seq1", "seq2", "seq3"}
        self.assertEqual(result, expected)

    @patch("openedx_user_groups.processors.user_group_partition_groups.is_user_groups_enabled")
    def test_usage_keys_to_remove_when_user_groups_disabled(self, mock_is_enabled: Mock):
        """Test usage_keys_to_remove when user groups are disabled."""
        mock_is_enabled.return_value = False
        # Create mock outline with exclusions
        section1 = MockOutlineSection("section1", {USER_GROUP_PARTITION_ID: {3, 4}})
        section1.sequences = [MockOutlineSequence("seq1", {})]
        full_course_outline = MockFullCourseOutline([section1])

        processor = UserGroupPartitionGroupsOutlineProcessor(self.course_key, self.user, self.at_time)
        result = processor.usage_keys_to_remove(full_course_outline)

        self.assertEqual(result, set())

    @patch("openedx_user_groups.processors.user_group_partition_groups.is_user_groups_enabled")
    def test_usage_keys_to_remove_with_empty_outline(self, mock_is_enabled: Mock):
        """Test usage_keys_to_remove with an empty course outline."""
        mock_is_enabled.return_value = True
        full_course_outline = MockFullCourseOutline([])

        processor = UserGroupPartitionGroupsOutlineProcessor(self.course_key, self.user, self.at_time)
        result = processor.usage_keys_to_remove(full_course_outline)

        self.assertEqual(result, set())

    @patch("openedx_user_groups.processors.user_group_partition_groups.is_user_groups_enabled")
    def test_usage_keys_to_remove_with_section_no_sequences(self, mock_is_enabled: Mock):
        """Test usage_keys_to_remove with a section that has no sequences."""
        mock_is_enabled.return_value = True
        # Create mock outline with section that has no sequences
        section1 = MockOutlineSection(
            "section1",
            {USER_GROUP_PARTITION_ID: {3, 4}},  # User not in these groups
        )
        section1.sequences = []
        full_course_outline = MockFullCourseOutline([section1])

        processor = UserGroupPartitionGroupsOutlineProcessor(self.course_key, self.user, self.at_time)
        processor.user_groups = [self.user_group_1, self.user_group_2]
        result = processor.usage_keys_to_remove(full_course_outline)

        expected = {"section1"}
        self.assertEqual(result, expected)

    @patch("openedx_user_groups.processors.user_group_partition_groups.is_user_groups_enabled")
    def test_integration_load_data_and_exclusion_logic(self, mock_is_enabled: Mock):
        """Integration test combining load_data and exclusion logic."""
        mock_is_enabled.return_value = True
        processor = UserGroupPartitionGroupsOutlineProcessor(self.course_key, self.user, self.at_time)
        # Mock the user groups that the user belongs to
        processor.user_groups = [self.user_group_1, self.user_group_2]

        # Test exclusion logic with user in some groups but not others
        result1 = processor._is_user_excluded_by_partition_group(
            {USER_GROUP_PARTITION_ID: {1, 3}}  # User in group 1, not in group 3
        )
        self.assertFalse(result1)  # Should not be excluded because user is in group 1

        result2 = processor._is_user_excluded_by_partition_group(
            {USER_GROUP_PARTITION_ID: {3, 4}}  # User not in either group
        )
        self.assertTrue(result2)  # Should be excluded because user is not in any group
