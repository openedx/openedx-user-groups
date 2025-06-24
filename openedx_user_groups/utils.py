"""Utility functions for the openedx_user_groups app."""


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
        "course": "course",  # When we have actual course models
        "courseoverview": "course",  # edx-platform course overview model
        "organization": "organization",  # Organization models
    }

    model_name = content_type.model
    return model_to_scope_mapping.get(model_name, "instance")  # Default to instance
