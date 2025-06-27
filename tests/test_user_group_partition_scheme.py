"""
Test Suite for the User Group Partition Scheme.

This test suite covers all classes and methods defined in `user_group_partition_scheme.py`.
"""

from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from opaque_keys.edx.keys import CourseKey

from openedx_user_groups.models import Scope, UserGroup, UserGroupMembership
from openedx_user_groups.partitions.user_group_partition_scheme import (
    USER_GROUP_PARTITION_ID,
    UserGroupPartition,
    UserGroupPartitionScheme,
    UserPartitionError,
    create_user_group_partition,
    create_user_group_partition_with_course_id,
)
from tests.factories import UserFactory

User = get_user_model()


class GroupMock:
    """Mock Group class for testing."""

    def __init__(self, id, name):  # pylint: disable=redefined-builtin
        self.id = id
        self.name = name

    def __eq__(self, other):
        """Compare GroupMock instances by their attributes."""
        if not isinstance(other, GroupMock):
            return False
        return self.id == other.id and self.name == other.name


class UserPartitionMock:
    """Mock UserPartition class for testing."""

    # pylint: disable=redefined-builtin, too-many-positional-arguments
    def __init__(self, id, name, description, groups, scheme, parameters, active=True):
        self.id = id
        self.name = name
        self.description = description
        self.groups = groups
        self.scheme = scheme
        self.parameters = parameters
        self.active = active


class TestUserGroupPartition(TestCase):
    """Test UserGroupPartition class."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data for UserGroupPartition tests."""
        cls.course_key = CourseKey.from_string("course-v1:OpenedX+Demo+Course")
        cls.course_content_type = ContentType.objects.get_for_model(User)

        cls.scope = Scope.objects.create(
            name="Demo Course Scope",
            description="Scope for the demo course",
            content_type=cls.course_content_type,
            object_id=1,
        )

        cls.user_group1 = UserGroup.objects.create(
            name="Test Group 1",
            description="First test group",
            scope=cls.scope,
            enabled=True,
        )

        cls.user_group2 = UserGroup.objects.create(
            name="Test Group 2",
            description="Second test group",
            scope=cls.scope,
            enabled=True,
        )

        cls.disabled_user_group = UserGroup.objects.create(
            name="Disabled Group",
            description="Disabled test group",
            scope=cls.scope,
            enabled=False,
        )

    @patch("openedx_user_groups.partitions.user_group_partition_scheme.Group")
    @patch("openedx_user_groups.partitions.user_group_partition_scheme.is_user_groups_enabled")
    def test_groups_property_when_enabled(self, mock_is_enabled: Mock, mock_group: Mock):
        """Test groups property returns enabled user groups when feature is enabled."""
        mock_is_enabled.return_value = True
        mock_group.side_effect = GroupMock

        partition = UserGroupPartition(
            id=USER_GROUP_PARTITION_ID,
            name="Test Partition",
            description="Test partition description",
            groups=[],
            scheme=UserGroupPartitionScheme,
            parameters={"course_id": str(self.course_key)},
        )

        groups = partition.groups
        # Should return only enabled user groups
        expected_group_ids = {self.user_group1.id, self.user_group2.id}
        expected_group_names = {self.user_group1.name, self.user_group2.name}

        actual_group_ids = {group.id for group in groups}
        actual_group_names = {group.name for group in groups}

        self.assertEqual(actual_group_ids, expected_group_ids)
        self.assertEqual(actual_group_names, expected_group_names)
        self.assertNotIn(self.disabled_user_group.id, actual_group_ids)
        self.assertNotIn(self.disabled_user_group.name, actual_group_names)

    @patch("openedx_user_groups.partitions.user_group_partition_scheme.is_user_groups_enabled")
    def test_groups_property_when_disabled(self, mock_is_enabled: Mock):
        """Test groups property returns empty list when feature is disabled."""
        mock_is_enabled.return_value = False

        partition = UserGroupPartition(
            id=USER_GROUP_PARTITION_ID,
            name="Test Partition",
            description="Test partition description",
            groups=[],
            scheme=UserGroupPartitionScheme,
            parameters={"course_id": str(self.course_key)},
        )

        groups = partition.groups
        self.assertEqual(groups, [])


class TestUserGroupPartitionScheme(TestCase):
    """Test UserGroupPartitionScheme class."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data for UserGroupPartitionScheme tests."""
        cls.course_key = CourseKey.from_string("course-v1:OpenedX+Demo+Course")
        cls.course_content_type = ContentType.objects.get_for_model(User)

        cls.scope = Scope.objects.create(
            name="Demo Course Scope",
            description="Scope for the demo course",
            content_type=cls.course_content_type,
            object_id=1,
        )

        cls.user_group1 = UserGroup.objects.create(
            name="Test Group 1",
            description="First test group",
            scope=cls.scope,
            enabled=True,
        )

        cls.user_group2 = UserGroup.objects.create(
            name="Test Group 2",
            description="Second test group",
            scope=cls.scope,
            enabled=True,
        )

        cls.user = UserFactory()

        # Create user group memberships
        cls.membership1 = UserGroupMembership.objects.create(
            user=cls.user,
            group=cls.user_group1,
            is_active=True,
        )

        cls.membership2 = UserGroupMembership.objects.create(
            user=cls.user,
            group=cls.user_group2,
            is_active=True,
        )

    def setUp(self):
        """Set up for each test method."""
        self.user_partition = UserPartitionMock(
            id=USER_GROUP_PARTITION_ID,
            name="Test Partition",
            description="Test partition description",
            groups=[],
            scheme=UserGroupPartitionScheme,
            parameters={"course_id": str(self.course_key)},
        )

    @patch("openedx_user_groups.partitions.user_group_partition_scheme.Group")
    @patch("openedx_user_groups.partitions.user_group_partition_scheme.is_user_groups_enabled")
    def test_get_group_for_user_when_enabled(self, mock_is_enabled: Mock, mock_group: Mock):
        """Test get_group_for_user returns user groups when feature is enabled."""
        mock_is_enabled.return_value = True
        mock_group.side_effect = GroupMock

        groups = UserGroupPartitionScheme.get_group_for_user(self.course_key, self.user, self.user_partition)

        # Should return groups for both user groups the user belongs to
        self.assertIsNotNone(groups)
        self.assertEqual(len(groups), 2)

        group_ids = [group.id for group in groups]
        group_names = [group.name for group in groups]

        self.assertIn(self.user_group1.id, group_ids)
        self.assertIn(self.user_group2.id, group_ids)
        self.assertIn(self.user_group1.name, group_names)
        self.assertIn(self.user_group2.name, group_names)

    @patch("openedx_user_groups.partitions.user_group_partition_scheme.is_user_groups_enabled")
    def test_get_group_for_user_when_disabled(self, mock_is_enabled: Mock):
        """Test get_group_for_user returns None when feature is disabled."""
        mock_is_enabled.return_value = False

        groups = UserGroupPartitionScheme.get_group_for_user(self.course_key, self.user, self.user_partition)

        self.assertIsNone(groups)

    @patch("openedx_user_groups.partitions.user_group_partition_scheme.is_user_groups_enabled")
    def test_get_group_for_user_no_memberships(self, mock_is_enabled: Mock):
        """Test get_group_for_user returns None when user has no memberships."""
        mock_is_enabled.return_value = True
        # Create user with no memberships
        user_without_memberships = UserFactory()

        groups = UserGroupPartitionScheme.get_group_for_user(
            self.course_key, user_without_memberships, self.user_partition
        )

        self.assertIsNone(groups)

    @patch("openedx_user_groups.partitions.user_group_partition_scheme.Group")
    @patch("openedx_user_groups.partitions.user_group_partition_scheme.is_user_groups_enabled")
    def test_get_group_for_user_inactive_memberships(self, mock_is_enabled: Mock, mock_group: Mock):
        """Test get_group_for_user ignores inactive memberships."""
        mock_is_enabled.return_value = True
        mock_group.side_effect = GroupMock
        # Deactivate one membership
        self.membership2.is_active = False
        self.membership2.save()

        groups = UserGroupPartitionScheme.get_group_for_user(self.course_key, self.user, self.user_partition)

        # Should only return the active membership
        self.assertIsNotNone(groups)
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].id, self.user_group1.id)

    @patch("openedx_user_groups.partitions.user_group_partition_scheme.is_user_groups_enabled")
    @patch("openedx_user_groups.partitions.user_group_partition_scheme.get_course_masquerade")
    @patch("openedx_user_groups.partitions.user_group_partition_scheme.is_masquerading_as_specific_student")
    @patch("openedx_user_groups.partitions.user_group_partition_scheme.get_masquerading_user_group")
    def test_get_group_for_user_with_masquerade(
        self,
        mock_get_masquerading_group: Mock,
        mock_is_masquerading: Mock,
        mock_get_masquerade: Mock,
        mock_is_enabled: Mock,
    ):
        """Test get_group_for_user handles masquerading correctly."""
        mock_is_enabled.return_value = True
        mock_get_masquerade.return_value = True
        mock_is_masquerading.return_value = False
        expected_groups = [GroupMock(id=1, name="Masquerade Group")]
        mock_get_masquerading_group.return_value = expected_groups

        groups = UserGroupPartitionScheme.get_group_for_user(self.course_key, self.user, self.user_partition)

        self.assertEqual(groups, expected_groups)
        mock_get_masquerading_group.assert_called_once_with(self.course_key, self.user, self.user_partition)

    @patch("openedx_user_groups.partitions.user_group_partition_scheme.is_user_groups_enabled")
    def test_create_user_partition_when_enabled(self, mock_is_enabled: Mock):
        """Test create_user_partition creates partition when feature is enabled."""
        mock_is_enabled.return_value = True

        partition = UserGroupPartitionScheme.create_user_partition(
            id=USER_GROUP_PARTITION_ID,
            name="Test Partition",
            description="Test partition description",
            parameters={"course_id": str(self.course_key)},
        )

        self.assertIsInstance(partition, UserGroupPartition)
        self.assertEqual(partition.id, USER_GROUP_PARTITION_ID)
        self.assertEqual(partition.name, "Test Partition")
        self.assertEqual(partition.description, "Test partition description")
        self.assertEqual(partition.scheme, UserGroupPartitionScheme)
        self.assertEqual(partition.parameters, {"course_id": str(self.course_key)})
        self.assertTrue(partition.active)

    @patch("openedx_user_groups.partitions.user_group_partition_scheme.is_user_groups_enabled")
    def test_create_user_partition_when_disabled(self, mock_is_enabled: Mock):
        """Test create_user_partition returns None when feature is disabled."""
        mock_is_enabled.return_value = False

        partition = UserGroupPartitionScheme.create_user_partition(
            id=USER_GROUP_PARTITION_ID,
            name="Test Partition",
            description="Test partition description",
            parameters={"course_id": str(self.course_key)},
        )

        self.assertIsNone(partition)

    @patch("openedx_user_groups.partitions.user_group_partition_scheme.Group")
    @patch("openedx_user_groups.partitions.user_group_partition_scheme.is_user_groups_enabled")
    def test_create_user_partition_with_groups(self, mock_is_enabled: Mock, mock_group: Mock):
        """Test create_user_partition with provided groups."""
        mock_is_enabled.return_value = True
        mock_group.side_effect = GroupMock
        test_groups = [GroupMock(id=1, name="Test Group 1"), GroupMock(id=2, name="Test Group 2")]

        partition = UserGroupPartitionScheme.create_user_partition(
            id=USER_GROUP_PARTITION_ID,
            name="Test Partition",
            description="Test partition description",
            groups=test_groups,
            parameters={"course_id": str(self.course_key)},
            active=False,
        )

        self.assertEqual(partition.groups, test_groups)
        self.assertFalse(partition.active)


class TestPartitionCreationFunctions(TestCase):
    """Test the partition creation helper functions."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data for partition creation function tests."""
        cls.course_key = CourseKey.from_string("course-v1:OpenedX+Demo+Course")

    @patch("openedx_user_groups.partitions.user_group_partition_scheme.is_user_groups_enabled")
    @patch("openedx_user_groups.partitions.user_group_partition_scheme.UserPartition")
    def test_create_user_group_partition_with_course_id_success(self, mock_user_partition: Mock, mock_is_enabled: Mock):
        """Test create_user_group_partition_with_course_id creates partition successfully."""
        mock_is_enabled.return_value = True

        mock_scheme = Mock()
        mock_scheme.create_user_partition.return_value = Mock()
        mock_user_partition.get_scheme.return_value = mock_scheme

        partition = create_user_group_partition_with_course_id(self.course_key)

        self.assertIsNotNone(partition)
        mock_scheme.create_user_partition.assert_called_once_with(
            id=USER_GROUP_PARTITION_ID,
            name="User Groups",
            description="Partition for segmenting users by user groups",
            parameters={"course_id": str(self.course_key)},
        )

    @patch("openedx_user_groups.partitions.user_group_partition_scheme.UserPartition")
    def test_create_user_group_partition_with_course_id_scheme_not_found(self, mock_user_partition: Mock):
        """Test create_user_group_partition_with_course_id handles missing scheme gracefully."""
        mock_user_partition.get_scheme.side_effect = UserPartitionError("Scheme not found")

        partition = create_user_group_partition_with_course_id(self.course_key)

        self.assertIsNone(partition)

    @patch("openedx_user_groups.partitions.user_group_partition_scheme.create_user_group_partition_with_course_id")
    @patch("openedx_user_groups.partitions.user_group_partition_scheme.is_user_groups_enabled")
    def test_create_user_group_partition_success(self, mock_is_enabled: Mock, mock_create_partition: Mock):
        """Test create_user_group_partition returns partition when feature is enabled."""
        mock_is_enabled.return_value = True
        course = Mock(id=self.course_key)

        partition = create_user_group_partition(course)

        self.assertIsNotNone(partition)
        mock_create_partition.assert_called_once_with(self.course_key)

    @patch("openedx_user_groups.partitions.user_group_partition_scheme.is_user_groups_enabled")
    def test_create_user_group_partition_disabled(self, mock_is_enabled: Mock):
        """Test create_user_group_partition returns empty list when feature is disabled."""
        mock_is_enabled.return_value = False
        course = Mock(id=self.course_key)

        partition = create_user_group_partition(course)

        self.assertEqual(partition, [])


class TestUserGroupPartitionSchemeIntegration(TestCase):
    """Integration tests for UserGroupPartitionScheme with real database operations."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data for integration tests."""
        cls.course_key = CourseKey.from_string("course-v1:OpenedX+Demo+Course")
        cls.course_content_type = ContentType.objects.get_for_model(User)

        cls.scope = Scope.objects.create(
            name="Demo Course Scope",
            description="Scope for the demo course",
            content_type=cls.course_content_type,
            object_id=1,
        )

        # Create multiple user groups
        cls.user_group1 = UserGroup.objects.create(
            name="Group A",
            description="First group",
            scope=cls.scope,
            enabled=True,
        )

        cls.user_group2 = UserGroup.objects.create(
            name="Group B",
            description="Second group",
            scope=cls.scope,
            enabled=True,
        )

        cls.user_group3 = UserGroup.objects.create(
            name="Group C",
            description="Third group",
            scope=cls.scope,
            enabled=False,  # Disabled group
        )

        # Create users
        cls.user1 = UserFactory()
        cls.user2 = UserFactory()
        cls.user3 = UserFactory()

        # Create memberships
        UserGroupMembership.objects.create(
            user=cls.user1,
            group=cls.user_group1,
            is_active=True,
        )

        UserGroupMembership.objects.create(
            user=cls.user2,
            group=cls.user_group2,
            is_active=True,
        )

        UserGroupMembership.objects.create(
            user=cls.user3,
            group=cls.user_group3,
            is_active=True,
        )

    def setUp(self):
        """Set up for each test method."""
        self.user_partition = UserPartitionMock(
            id=USER_GROUP_PARTITION_ID,
            name="Test Partition",
            description="Test partition description",
            groups=[],
            scheme=UserGroupPartitionScheme,
            parameters={"course_id": str(self.course_key)},
        )

    def _assert_single_group(self, groups: list[GroupMock], expected_group: GroupMock):
        """Helper method to assert a single group assignment."""
        self.assertIsNotNone(groups)
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].id, expected_group.id)
        self.assertEqual(groups[0].name, expected_group.name)

    @patch("openedx_user_groups.partitions.user_group_partition_scheme.Group")
    @patch("openedx_user_groups.partitions.user_group_partition_scheme.is_user_groups_enabled")
    def test_integration_user_group_assignment(self, mock_is_enabled: Mock, mock_group: Mock):
        """Test that users are correctly assigned to their user groups."""
        mock_is_enabled.return_value = True
        mock_group.side_effect = GroupMock

        # Test user1 should be in Group A
        groups1 = UserGroupPartitionScheme.get_group_for_user(self.course_key, self.user1, self.user_partition)
        self._assert_single_group(groups1, self.user_group1)

        # Test user2 should be in Group B
        groups2 = UserGroupPartitionScheme.get_group_for_user(self.course_key, self.user2, self.user_partition)
        self._assert_single_group(groups2, self.user_group2)

        # Test user3 should not be in any group (since Group C is disabled)
        groups3 = UserGroupPartitionScheme.get_group_for_user(self.course_key, self.user3, self.user_partition)
        self.assertEqual(groups3, [])

    @patch("openedx_user_groups.partitions.user_group_partition_scheme.Group")
    @patch("openedx_user_groups.partitions.user_group_partition_scheme.is_user_groups_enabled")
    def test_integration_multiple_memberships(self, mock_is_enabled: Mock, mock_group: Mock):
        """Test that users with multiple memberships get all their groups."""
        mock_is_enabled.return_value = True
        mock_group.side_effect = GroupMock

        # Add user1 to Group B as well
        UserGroupMembership.objects.create(
            user=self.user1,
            group=self.user_group2,
            is_active=True,
        )

        groups = UserGroupPartitionScheme.get_group_for_user(self.course_key, self.user1, self.user_partition)
        self.assertIsNotNone(groups)
        self.assertEqual(len(groups), 2)
        expected_group_ids = {self.user_group1.id, self.user_group2.id}
        actual_group_ids = {group.id for group in groups}
        self.assertEqual(actual_group_ids, expected_group_ids)

    @patch("openedx_user_groups.partitions.user_group_partition_scheme.Group")
    @patch("openedx_user_groups.partitions.user_group_partition_scheme.is_user_groups_enabled")
    def test_integration_partition_groups_property(self, mock_is_enabled: Mock, mock_group: Mock):
        """Test that partition groups property returns only enabled groups."""
        mock_is_enabled.return_value = True
        mock_group.side_effect = GroupMock

        partition = UserGroupPartition(
            id=USER_GROUP_PARTITION_ID,
            name="Test Partition",
            description="Test partition description",
            groups=[],
            scheme=UserGroupPartitionScheme,
            parameters={"course_id": str(self.course_key)},
        )

        groups = partition.groups
        # Should only return enabled groups
        expected_group_ids = {self.user_group1.id, self.user_group2.id}
        actual_group_ids = {group.id for group in groups}
        self.assertEqual(actual_group_ids, expected_group_ids)
        self.assertNotIn(self.user_group3.id, actual_group_ids)  # Disabled group should not be included
