"""
Core models for Open edX User Groups.

In this module, we define the core models that represent user groups within the Open edX platform. Here's a high level
overview of the module:

Models:
- UserGroup: Represents a group of users within the Open edX platform, allowing for the management and organization of
users into distinct groups.
- UserGroupMembership: Represents the memberships of users within user groups, linking users to their respective
groups.
- Criterion: Represents a criterion that can be used to filter or categorize user groups based on specific attributes or
behaviors.
- Scope: Represents the scope of a user group, defining the context in which the group operates, such as course or
site-wide.

With the following relationships:
- UserGroup has many UserGroupMembership, linking users to their respective groups.
- UserGroupMembership belongs to a UserGroup and a User, establishing the relationship between users and their
groups. This includes a many-to-many relationship between users and groups, allowing associating metadata to
the relationship when created.
- UserGroup can have many Criteria, allowing for the categorization of user groups based on specific attributes or
behaviors.
- A criterion is associated with a single UserGroup, allowing for filtering of user groups based on specific
attributes only for that group.
- Scope can be associated with a UserGroup, defining the context in which the group operates. A user group can
be associated only with one scope at a time.

This module is not meant for production, it's only for POC purposes.
"""

import json

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.functional import cached_property
from pydantic_core import from_json

from openedx_user_groups.backends import DjangoORMBackendClient
from openedx_user_groups.manager import CriterionManager

User = get_user_model()


def validate_criterion_type(value):
    """Validate that the criterion type is one of the available types.

    Args:
        value (str): The criterion type to validate.

    Raises:
        ValidationError: If the criterion type is not one of the available types.
    """
    try:
        available_types = Criterion.available_criterion_types()
        if value not in available_types:
            raise ValidationError(
                f"'{value}' is not a valid criterion type. "
                f"Available types: {', '.join(available_types)}"
            )
    except AttributeError:
        # If CriterionManager is not implemented yet, skip validation
        pass


class Scope(models.Model):
    """Represents the scope of a user group.

    Attributes:
        name (str): The name of the scope.
        description (str): A brief description of the scope. Could be used for annotation purposes.
        content_type (ForeignKey): The content type of the object that defines the scope.
        object_id (PositiveIntegerField): The ID of the object that defines the scope.
        content_object (GenericForeignKey): The object that defines the scope (e.g., course, organization).
    .. no_pii:
    """

    name = models.CharField(
        max_length=255
    )  # TODO: should we use something like: display_name?
    description = models.TextField(blank=True, null=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.CharField(max_length=255)
    content_object = GenericForeignKey(
        "content_type", "object_id"
    )  # TODO: how can we display this in a nice way?


class UserGroup(models.Model):
    """Represents a group of users within the Open edX platform.

    This model allows for the management and organization of users into distinct groups.

    Attributes:
        name (str): The name of the user group.
        description (str): A brief description of the user group.
        last_membership_change (datetime): The timestamp of the last change to the user group membership
        related to the group.
        enabled (bool): Whether the user group is enabled.
        scope (str): The scope of the user group, defining the context in which it operates.
        users (ManyToManyField): The users that are members of the group.
    .. no_pii:
    """

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    last_membership_change = models.DateTimeField(auto_now=True)
    enabled = models.BooleanField(default=True)
    scope = models.ForeignKey(
        Scope,
        on_delete=models.CASCADE,
        related_name="user_groups",
    )
    users = models.ManyToManyField(User, through="UserGroupMembership")

    class Meta:
        ordering = ["name"]
        unique_together = [
            "name",
            "scope",
        ]  # A group name should be unique within a scope

    # TODO: should we enforce here the group's scope is the same as the criteria's scope here before saving or in the API?

    def save(self, *args, **kwargs):
        """Save the user group.

        This method is overriden to:
        - Prevent the scope of an existing user group from being changed.
        """
        if self.pk is not None:
            original = UserGroup.objects.get(pk=self.pk)
            if original.scope != self.scope:
                raise ValueError("Cannot change the scope of an existing user group")
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    def criteria_templates(self):
        """Return the criterion templates (classes) for the user group.

        Returns:
            list: A list of criterion templates (classes).
        """
        return [criterion.criterion_type_template for criterion in self.criteria.all()]


class UserGroupMembership(models.Model):
    """Represents the membership of a user in a user group.

    This model allows for the management and organization of users into distinct groups.

    Attributes:
        user (User): The user who is a member of the group.
        group (UserGroup): The group to which the user belongs.
        joined_at (datetime): The timestamp when the user joined the group.
        left_at (datetime): The timestamp when the user left the group.
        is_active (bool): Whether the user is still a member of the group.
    .. no_pii:
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    group = models.ForeignKey(UserGroup, on_delete=models.CASCADE)
    joined_at = models.DateTimeField(auto_now_add=True)
    left_at = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.username} - {self.group.name}"


class Criterion(models.Model):
    """Represents a criterion that can be used to filter or categorize user groups based on specific attributes or
    behaviors.

    Attributes:
        criterion_type (str): The type of the criterion. This is the name of the criterion type class used as a key to
         load the class from the CriterionManager.
        criterion_operator (str): The operator of the criterion.
        criterion_config (dict): The configuration of the criterion.
        group (UserGroup): The group to which the criterion belongs.
    .. no_pii:
    """

    criterion_type = models.CharField(
        max_length=255,  # When creating a new criterion, this should be one of the available criterion types.
        validators=[validate_criterion_type],
        help_text="Must be one of the available criterion types from CriterionManager",
    )
    criterion_operator = models.CharField(max_length=255)
    criterion_config = models.JSONField(default=dict)
    user_group = models.ForeignKey(
        UserGroup, on_delete=models.CASCADE, related_name="criteria"
    )

    class Meta:
        ordering = ["criterion_type"]

    def __str__(self):
        return f"{self.criterion_type} - {self.user_group.name}"

    @staticmethod
    def available_criterion_types():
        return CriterionManager.get_criterion_types()

    @property
    def criterion_type_template(self):
        return CriterionManager.get_criterion_class_by_type(self.criterion_type)

    @property
    def criterion_instance(self):
        """Return the criterion instanced with the current configuration.

        Returns:
            BaseCriterionType: The criterion instance.
        """
        return self.criterion_type_template(
            self.criterion_operator,
            self.criterion_config,
            self.user_group.scope,
            DjangoORMBackendClient(),
        )

    @cached_property
    def config(self):
        return from_json(self.criterion_config)


class GroupCollection(models.Model):
    """Represents a collection of user groups.

    Attributes:
        name (str): The name of the group collection.
        description (str): A brief description of the group collection.
    .. no_pii:
    """

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    user_groups = models.ManyToManyField(UserGroup, related_name="group_collections")

    def __str__(self):
        return self.name
