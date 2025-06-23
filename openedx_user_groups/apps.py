"""
openedx_user_groups Django application initialization.
"""

from django.apps import AppConfig


class OpenedxUserGroupsConfig(AppConfig):
    """
    Configuration for the openedx_user_groups Django application.
    """

    name = "openedx_user_groups"
    default_auto_field = "django.db.models.BigAutoField"

    def ready(self):
        """
        Perform application initialization.

        This method connects the handler to all events that trigger updates to the user groups.
        """
        from openedx_user_groups.criteria import BaseCriterionType
        from openedx_user_groups.handlers import handle_user_group_update

        for event in BaseCriterionType.get_all_updated_by_events():
            event.connect(handle_user_group_update)
