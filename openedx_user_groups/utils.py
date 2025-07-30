"""Utility functions for the openedx_user_groups app."""

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from organizations.models import Organization

try:
    from opaque_keys.edx.keys import CourseKey
    from openedx.core.djangoapps.content.course_overviews.models import CourseOverview
except ImportError:
    CourseKey = None
    CourseOverview = None


def get_scope_type_from_content_type(content_type):
    """
    Map Django ContentType to scope type names used by criteria.

    Args:
        content_type: Django ContentType instance

    Returns:
        str: Scope type name (e.g., "course", "organization", "instance")
    """
    # Mapping from Django model names to scope types
    model_to_scope_mapping = {
        "courseoverview": "course",  # edx-platform course overview model
        "organization": "organization",  # Organization models
    }

    model_name = content_type.model
    return model_to_scope_mapping.get(model_name, "instance")  # Default to instance


def process_content_object(content_object_data):
    """
    Process content_object data to get the correct ContentType and object_id.

    Args:
        content_object_data: Dict with content_type_model and object_id

    Returns:
        tuple: (ContentType, object_id)
    """
    content_type_model = content_object_data["content_type_model"]
    object_id = content_object_data["object_id"]

    if content_type_model == "courseoverview":
        # Validate course exists and use course key directly
        course_key = CourseKey.from_string(object_id)
        CourseOverview.get_from_id(course_key)  # Validates existence
        return (
            ContentType.objects.get(
                app_label="course_overviews", model="courseoverview"
            ),
            object_id,
        )
    elif content_type_model == "organization":
        # Validate organization exists and use short_name directly
        Organization.objects.get(short_name=object_id)  # Validates existence
        return (
            ContentType.objects.get(app_label="organizations", model="organization"),
            object_id,
        )
    else:
        # Generic case - assume app_label equals content_type_model
        # TODO: this needs support for what we're considering to be instance-level scope.
        return (
            ContentType.objects.get(
                app_label=content_type_model, model=content_type_model
            ),
            object_id,
        )
