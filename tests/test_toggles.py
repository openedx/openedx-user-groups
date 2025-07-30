"""
Test Suite for the User Group toggles.

This test suite covers all toggle functionality defined in toggles.py.
"""

from unittest.mock import Mock, patch

from django.test import TestCase
from opaque_keys.edx.keys import CourseKey

from openedx_user_groups.toggles import ENABLE_USER_GROUPS, WAFFLE_FLAG_NAMESPACE, is_user_groups_enabled


class TestToggles(TestCase):
    """Test toggle functionality and configuration."""

    def test_waffle_flag_namespace(self):
        """Test that the waffle flag namespace is correctly defined.

        Expected Results:
        - The namespace should be "user_groups".
        """
        self.assertEqual(WAFFLE_FLAG_NAMESPACE, "user_groups")

    def test_enable_user_groups_flag_creation(self):
        """Test that the ENABLE_USER_GROUPS flag is created with correct parameters.

        Expected Results:
        - The flag should be created with the correct namespace and module name.
        """
        expected_flag_name = f"{WAFFLE_FLAG_NAMESPACE}.enable_user_groups"
        self.assertEqual(ENABLE_USER_GROUPS.name, expected_flag_name)
        self.assertEqual(ENABLE_USER_GROUPS.module_name, "openedx_user_groups.toggles")

    @patch("openedx_user_groups.toggles.ENABLE_USER_GROUPS")
    def test_is_user_groups_enabled_when_flag_enabled(self, mock_flag: Mock):
        """Test is_user_groups_enabled returns True when flag is enabled.

        Expected Results:
        - The function should return True when the waffle flag is enabled.
        """
        course_key = CourseKey.from_string("course-v1:edX+Demo+Course")
        mock_flag.is_enabled.return_value = True

        result = is_user_groups_enabled(course_key)

        self.assertTrue(result)
        mock_flag.is_enabled.assert_called_once_with(course_key)

    @patch("openedx_user_groups.toggles.ENABLE_USER_GROUPS")
    def test_is_user_groups_enabled_when_flag_disabled(self, mock_flag: Mock):
        """Test is_user_groups_enabled returns False when flag is disabled.

        Expected Results:
        - The function should return False when the waffle flag is disabled.
        """
        course_key = CourseKey.from_string("course-v1:edX+Demo+Course")
        mock_flag.is_enabled.return_value = False

        result = is_user_groups_enabled(course_key)

        self.assertFalse(result)
        mock_flag.is_enabled.assert_called_once_with(course_key)

    @patch("openedx_user_groups.toggles.ENABLE_USER_GROUPS")
    def test_is_user_groups_enabled_with_different_course_keys(self, mock_flag: Mock):
        """Test is_user_groups_enabled works with different course key formats.

        Expected Results:
        - The function should work correctly with different course key formats.
        """
        course_keys = [
            CourseKey.from_string("course-v1:edX+Demo+Course"),
            CourseKey.from_string("course-v1:TestOrg+CS101+2024"),
            CourseKey.from_string("course-v1:AnotherOrg+Math101+Fall2024"),
        ]
        mock_flag.is_enabled.return_value = True

        for course_key in course_keys:
            result = is_user_groups_enabled(course_key)
            self.assertTrue(result)
            mock_flag.is_enabled.assert_called_with(course_key)

    @patch("openedx_user_groups.toggles.ENABLE_USER_GROUPS")
    def test_is_user_groups_enabled_flag_called_with_correct_arguments(self, mock_flag: Mock):
        """Test that the flag is called with the correct course key argument.

        Expected Results:
        - The waffle flag should be called with the exact course key passed to the function.
        """
        course_key = CourseKey.from_string("course-v1:edX+Demo+Course")
        mock_flag.is_enabled.return_value = True

        is_user_groups_enabled(course_key)

        mock_flag.is_enabled.assert_called_once_with(course_key)
        # Verify the course key is the same object, not just equal
        called_course_key = mock_flag.is_enabled.call_args[0][0]
        self.assertEqual(called_course_key, course_key)


class TestToggleIntegration(TestCase):
    """Test toggle integration with course keys and real scenarios."""

    def setUp(self):
        """Set up test data."""
        self.course_key = CourseKey.from_string("course-v1:edX+Demo+Course")

    @patch("openedx_user_groups.toggles.ENABLE_USER_GROUPS")
    def test_toggle_with_real_course_key_objects(self, mock_flag: Mock):
        """Test toggle functionality with real CourseKey objects.

        Expected Results:
        - The toggle should work correctly with real CourseKey objects.
        """
        mock_flag.is_enabled.return_value = True

        result = is_user_groups_enabled(self.course_key)

        self.assertTrue(result)
        mock_flag.is_enabled.assert_called_once_with(self.course_key)

    @patch("openedx_user_groups.toggles.ENABLE_USER_GROUPS")
    def test_toggle_behavior_consistency(self, mock_flag: Mock):
        """Test that toggle behavior is consistent across multiple calls.

        Expected Results:
        - Multiple calls with the same course key should return the same result.
        """
        mock_flag.is_enabled.return_value = True

        result1 = is_user_groups_enabled(self.course_key)
        result2 = is_user_groups_enabled(self.course_key)
        result3 = is_user_groups_enabled(self.course_key)

        self.assertTrue(result1)
        self.assertTrue(result2)
        self.assertTrue(result3)
        self.assertEqual(mock_flag.is_enabled.call_count, 3)

    @patch("openedx_user_groups.toggles.ENABLE_USER_GROUPS")
    def test_toggle_with_different_course_keys_returns_different_results(self, mock_flag: Mock):
        """Test that different course keys can have different toggle states.

        Expected Results:
        - Different course keys can have different toggle states.
        """
        course_key1 = CourseKey.from_string("course-v1:edX+Demo+Course")
        course_key2 = CourseKey.from_string("course-v1:TestOrg+CS101+2024")

        # Configure mock to return different values for different course keys
        def mock_is_enabled(course_key):
            if str(course_key) == "course-v1:edX+Demo+Course":
                return True
            return False

        mock_flag.is_enabled.side_effect = mock_is_enabled

        result1 = is_user_groups_enabled(course_key1)
        result2 = is_user_groups_enabled(course_key2)

        self.assertTrue(result1)
        self.assertFalse(result2)
        self.assertEqual(mock_flag.is_enabled.call_count, 2)
