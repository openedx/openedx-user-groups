"""
Core models for Open edX User Groups.

In this module, we define the core models that represent user groups within the Open edX platform. Currently,
it includes:

Models:
- UserGroup: Represents a group of users within the Open edX platform, allowing for the management and organization of
users into distinct groups.
- UserGroupMembership: Represents the memberships of users within user groups, linking users to their respective
groups.
- Criterion: Represents a criterion that can be used to filter or categorize user groups based on specific attributes or
behaviors.
- Scope: Represents the scope of a user group, defining the context in which the group operates, such as course or
site-wide. TODO: Add this model later on.

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
"""
from django.db import models

from django.contrib.auth import get_user_model

User = get_user_model()


class UserGroup(models.Model):
    """Represents a group of users within the Open edX platform.

    This model allows for the management and organization of users into distinct groups.

    Attributes:
        name (str): The name of the user group.
        description (str): A brief description of the user group.
        created_at (datetime): The timestamp when the user group was created.
        updated_at (datetime): The timestamp when the user group was last updated.
        last_membership_change (datetime): The timestamp of the last change to the user group membership
        related to the group.
        enabled (bool): Whether the user group is enabled.
        scope (str): The scope of the user group, defining the context in which it operates.
        users (ManyToManyField): The users that are members of the group.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_membership_change = models.DateTimeField(auto_now=True)
    enabled = models.BooleanField(default=True)
    scope = models.ForeignKey(Scope, on_delete=models.CASCADE, blank=True, null=True)
    users = models.ManyToManyField(User, through='UserGroupMembership')

    class Meta:
        ordering = ['name']
        unique_together = ['id', 'scope']


    def __str__(self):
        return self.name

    def get_users(self):
        return self.users.all()

    def get_criteria(self):
        return self.criteria.all()


class UserGroupMembership(models.Model):
    """Represents the membership of a user in a user group.

    This model allows for the management and organization of users into distinct groups.

    Attributes:
        user (User): The user who is a member of the group.
        group (UserGroup): The group to which the user belongs.
        joined_at (datetime): The timestamp when the user joined the group.
        left_at (datetime): The timestamp when the user left the group.
        is_active (bool): Whether the user is still a member of the group.
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
        name (str): The name of the criterion.
        description (str): A brief description of the criterion.
        criterion_type (str): The type of the criterion.
        criterion_operator (str): The operator of the criterion.
        criterion_config (dict): The configuration of the criterion.
        group (UserGroup): The group to which the criterion belongs.
    """

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    criterion_type = models.CharField(max_length=255) # TODO: Although right now there is no restriction on the type, we should only allow for registered criteria types
    criterion_operator = models.CharField(max_length=255) # TODO: Replace this with Enum later on
    criterion_config = models.JSONField(default=dict) # No restrictions needed on the config, each criterion type will have its own config and validate it accordingly
    group = models.ForeignKey(UserGroup, on_delete=models.CASCADE, related_name='criteria')

    def __str__(self):
        return f"{self.name} - {self.group.name}"

    def get_criterion_type(self):
        return self.criterion_type # TODO: Replace this with a method that returns the criterion type class as an object

    def get_criterion_operator(self):
        return self.criterion_operator # TODO: Replace this so it returns the enum supported type? Is it needed?

    def get_criterion_config(self):
        return self.criterion_config # Would I need to return the config as a dict?


class Scope(models.Model):
    """Represents the scope of a user group.

    Attributes:
        name (str): The name of the scope.
        description (str): A brief description of the scope.
        created_at (datetime): The timestamp when the scope was created.
        updated_at (datetime): The timestamp when the scope was last updated.
    """

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    resource_type = models.CharField(max_length=255) # TODO: Replace this with an Enum, it should only be allowed to be one of the following: course, org or site. Maybe more?
    resource_id = models.CharField(max_length=255) # TODO: Replace this with an actual opaque key or corresponding ID?

    def __str__(self):
        return f"{self.name} - {self.resource_type} - {self.resource_id}"

    def get_resource_type(self):
        return self.resource_type
    