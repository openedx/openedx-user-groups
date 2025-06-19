"""
Toggles for user groups.

This module defines feature flags (waffle flags) used to enable or disable functionality related to user groups
within the Open edX platform. These toggles allow for dynamic control of features without requiring code changes.
"""

from opaque_keys.edx.keys import CourseKey

try:
    from openedx.core.djangoapps.waffle_utils import CourseWaffleFlag
except ImportError:
    CourseWaffleFlag = None

# Namespace for all user group related waffle flags
WAFFLE_FLAG_NAMESPACE = "user_groups"

# .. toggle_name: user_groups.enable_user_groups
# .. toggle_implementation: CourseWaffleFlag
# .. toggle_default: False
# .. toggle_description: Waffle flag to enable or disable the user groups feature in a course.
# .. toggle_use_cases: temporary, open_edx
# .. toggle_creation_date: 2025-06-19
# .. toggle_target_removal_date: None
ENABLE_USER_GROUPS = CourseWaffleFlag(f"{WAFFLE_FLAG_NAMESPACE}.enable_user_groups", __name__)


def is_user_groups_enabled(course_key: CourseKey) -> bool:
    """
    Returns a boolean if user groups are enabled for the course.
    """
    return ENABLE_USER_GROUPS.is_enabled(course_key)
