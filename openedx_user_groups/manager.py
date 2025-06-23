"""This module is responsible for loading the criterion classes as plugins.

Here's a high level overview of the module:
- The CriterionManager subclassed the PluginManager class from edx-django-utils to implement the plugin discovery
for the criterion types.
- The criterion types should be registered in the _criterion_registry dictionary (FOR NOW).
- Ideally, we would use the PluginManager to discover the criterion types installed by plugins following this
format:
    "openedx_user_groups.criteria": [
        "last_login = openedx_user_groups.criteria.examples:LastLoginCriterion",
        "enrollment_mode = openedx_user_groups.criteria.examples:EnrollmentModeCriterion",
    ]
"""

from collections import OrderedDict

from edx_django_utils.plugins import PluginManager
from stevedore.extension import ExtensionManager

from openedx_user_groups.criteria import BaseCriterionType


class CriterionManager(PluginManager):
    """Manager for criterion types."""

    NAMESPACE = "openedx_user_groups.criteria"

    # Simple registry for POC - in production this would use plugin discovery
    # Format matches entry points: "name = module.path:ClassName"
    # TODO: what if I install a new one with the same name and override the old one? Log the override for the time being.
    # TODO: maybe we can consider using a mirror to INSTALLED_APPS to check if the criterion is already registered? AND manage duplicates like this?
    # TODO: Maybe default criterion shouldn't be registered as plugins?
    _criterion_registry = {
        "last_login": "openedx_user_groups.criteria_types:LastLoginCriterion",
        "course_enrollment": "openedx_user_groups.criteria_types:CourseEnrollmentCriterion",
        "manual": "openedx_user_groups.criteria_types:ManualCriterion",
        "enrollment_mode": "openedx_user_groups.criteria_types:EnrollmentModeCriterion",
        "enrolled_with_specific_mode": "openedx_user_groups.criteria_types:EnrollmentModeCriterion",
        "user_staff_status": "openedx_user_groups.criteria_types:UserStaffStatusCriterion",
    }

    @classmethod
    def get_criterion_types(cls):
        """Return list of available criterion type names."""
        # TODO: should be get_available_plugins(), but for now this is the closest we're going to implement.
        return OrderedDict(cls._criterion_registry)

    @classmethod
    def get_criterion_type_by_type(cls, criterion_type):
        """Return the criterion type module path for a given name."""
        # TODO: use simplest approach for POC
        return cls._criterion_registry.get(criterion_type, f"Unknown_{criterion_type}")

    @classmethod
    def get_criterion_class_by_type(cls, criterion_type):
        """Load and return the actual criterion class for a given name."""
        module_path = cls.get_criterion_type_by_type(criterion_type)
        if module_path.startswith(
            "Unknown_"
        ):  # TODO: should we raise an error instead?
            return None

        module_name, class_name = module_path.split(":")
        module = __import__(module_name, fromlist=[class_name])
        return getattr(module, class_name)


def load_criterion_class(criterion_type: str) -> BaseCriterionType:
    """Load a criterion class by type.

    Args:
        criterion_type (str): The type of the criterion to load.

    Returns:
        BaseCriterionType: The criterion class.
    """
    return CriterionManager.get_criterion_class_by_type(criterion_type)
