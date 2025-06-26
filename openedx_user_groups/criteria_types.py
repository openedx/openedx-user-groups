"""Module for the criteria types that implement different logic for evaluating the membership of a user group.

Here's a high level overview of the module:
- The criteria types are classes that inherit from the BaseCriterionType class.
- They implement the evaluate method, which is used to evaluate the criterion to determine the lists of users that match the criterion.
- Each criterion implements the evaluate method differently, based on the logic of the criterion. For example, the LastLoginCriterion evaluates the last login of the user,
while the CourseEnrollmentCriterion evaluates the course enrollment of the user.
- These criteria must be registered in the CriterionManager class so they can be loaded dynamically and be used by user groups.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Type

import attr
from django.db.models import Exists, OuterRef, Q, QuerySet
from django.utils import timezone
from openedx_events.learning.data import UserData
from openedx_events.learning.signals import (
    COURSE_ENROLLMENT_CHANGED,
    COURSE_ENROLLMENT_CREATED,
    SESSION_LOGIN_COMPLETED,
)
from openedx_events.tooling import OpenEdxPublicSignal
from pydantic import BaseModel, Field

from openedx_user_groups.backends import BackendClient
from openedx_user_groups.criteria import BaseCriterionType, ComparisonOperator
from openedx_user_groups.events import USER_STAFF_STATUS_CHANGED
from openedx_user_groups.models import Scope


class ManualCriterion(BaseCriterionType):
    """A criterion that is used to push a given list of users to a group."""

    criterion_type: str = "manual"
    description: str = (
        "A criterion that is used to push a given list of users to a group."
    )

    class ConfigModel(BaseModel):
        """Configuration model for manual criterion."""

        model_config = {
            "title": "Manual Criterion Configuration",
            "description": "Configuration for manually specifying users by username or email",
        }

        usernames_or_emails: List[str] = Field(
            description="List of usernames or email addresses to include in the group",
            examples=[["user1", "user2@example.com", "user3"]],
            min_length=1,
        )

    # Supported operators for this criterion type
    supported_operators: List[ComparisonOperator] = [
        ComparisonOperator.IN,
        ComparisonOperator.NOT_IN,
    ]

    def evaluate(self) -> QuerySet:
        """
        Evaluate the criterion.
        """
        return self.backend_client.get_users(
            self.scope
        ).filter(  # TODO: Currently side-wide, but should be filtered by scope
            Q(username__in=self.criterion_config.usernames_or_emails)
            | Q(email__in=self.criterion_config.usernames_or_emails)
        )


class CourseEnrollmentCriterion(BaseCriterionType):
    """A criterion that is used to evaluate the membership of a user group based on the course enrollment mode of the user."""

    updated_by_events = [COURSE_ENROLLMENT_CREATED, COURSE_ENROLLMENT_CHANGED]
    criterion_type: str = "course_enrollment"
    description: str = (
        "A criterion that is used to evaluate the membership of a user group based on the course enrollment mode of the user."
    )

    # TODO: should we use a single criterion with multiple attributes to filter by: mode, enrollment date, etc.? This would be an example of how we could do it, instead of having multiple criteria with specific attributes?
    class ConfigModel(BaseModel):
        """Configuration model for course enrollment criterion."""

        model_config = {
            "title": "Course Enrollment Criterion Configuration",
            "description": "Configuration for filtering users based on their course enrollment details",
        }

        mode: Optional[str] = Field(
            default=None,
            description="Enrollment mode to filter by (e.g., 'audit', 'verified', 'honor')",
            examples=["audit", "verified", "honor"],
        )
        enrollment_date: Optional[datetime] = Field(
            default=None,
            description="Filter users enrolled on or after this date",
            examples=["2024-01-01T00:00:00Z"],
        )

    supported_operators: List[ComparisonOperator] = [
        ComparisonOperator.IN,
        ComparisonOperator.NOT_IN,
        ComparisonOperator.EQUAL,
        ComparisonOperator.NOT_EQUAL,
        ComparisonOperator.GREATER_THAN,
        ComparisonOperator.GREATER_THAN_OR_EQUAL,
        ComparisonOperator.LESS_THAN,
        ComparisonOperator.LESS_THAN_OR_EQUAL,
    ]
    scopes: List[str] = ["course"]
    updated_by_events = [COURSE_ENROLLMENT_CREATED, COURSE_ENROLLMENT_CHANGED]

    def evaluate(self) -> QuerySet:
        """Evaluate the criterion and return users based on enrollment criteria."""
        filters = {}
        if self.criterion_config.mode:
            filters["mode"] = self.criterion_config.mode
        if self.criterion_config.enrollment_date:
            filters["created__gte"] = self.criterion_config.enrollment_date

        # Use Exists() for better performance - single query with subquery
        # TODO: needs to be tested for performance, always try enforcing a single query if possible.
        enrollments_subquery = self.backend_client.get_enrollments(self.scope).filter(
            user=OuterRef("pk"), **filters
        )
        return self.backend_client.get_users(self.scope).filter(
            Exists(enrollments_subquery)
        )


class LastLoginCriterion(BaseCriterionType):
    """A criterion that is used to evaluate the membership of a user group based on the last login of the user."""

    updated_by_events = [SESSION_LOGIN_COMPLETED]
    criterion_type: str = "last_login"
    description: str = (
        "A criterion that is used to evaluate the membership of a user group based on the last login of the user."
    )

    class ConfigModel(BaseModel):
        """Configuration model for last login criterion."""

        model_config = {
            "title": "Last Login Criterion Configuration",
            "description": "Configuration for filtering users based on their last login activity",
        }

        days: int = Field(
            description="Number of days since last login to use for comparison",
            examples=[1, 7, 30, 90],
            ge=0,
        )  # TODO: can we use a single criterion with multiple attributes to filter by: days, country, etc.?

    supported_operators: List[ComparisonOperator] = [
        ComparisonOperator.EQUAL,
        ComparisonOperator.NOT_EQUAL,
        ComparisonOperator.GREATER_THAN,
        ComparisonOperator.GREATER_THAN_OR_EQUAL,
        ComparisonOperator.LESS_THAN,
        ComparisonOperator.LESS_THAN_OR_EQUAL,
    ]

    def evaluate(self) -> QuerySet:
        """
        Evaluate the criterion.

        The config.days represents "days since last login":
        - GREATER_THAN 1 day = users who logged in more than 1 day ago (older login)
        - LESS_THAN 1 day = users who logged in less than 1 day ago (more recent login)
        """
        # Map operators to Django lookup operations
        # For "days since last login" logic:
        # - GREATER_THAN X days = last_login < (now - X days) [older than X days]
        # - LESS_THAN X days = last_login > (now - X days) [more recent than X days]
        # TODO: extract this to a helper function (backend so it's criteria agnostic)?
        queryset_operator_mapping = {
            ComparisonOperator.EQUAL: "exact",  # exactly X days ago (rarely used for datetime)
            ComparisonOperator.NOT_EQUAL: "exact",  # not exactly X days ago
            ComparisonOperator.GREATER_THAN: "lt",  # more than X days ago (older)
            ComparisonOperator.GREATER_THAN_OR_EQUAL: "lte",  # X days ago or older
            ComparisonOperator.LESS_THAN: "gt",  # less than X days ago (more recent)
            ComparisonOperator.LESS_THAN_OR_EQUAL: "gte",  # X days ago or more recent
        }

        threshold_date = timezone.now() - timedelta(days=self.criterion_config.days)
        query = {
            "last_login__"
            + queryset_operator_mapping[self.criterion_operator]: threshold_date
        }
        return self.backend_client.get_users(self.scope).filter(**query)


class EnrollmentModeCriterion(BaseCriterionType):
    """A criterion that is used to evaluate the membership of a user group based on the enrollment mode of the user."""

    updated_by_events = [COURSE_ENROLLMENT_CREATED, COURSE_ENROLLMENT_CHANGED]
    criterion_type: str = "enrollment_mode"
    description: str = (
        "A criterion that is used to evaluate the membership of a user group based on the enrollment mode of the user."
    )

    class ConfigModel(BaseModel):
        mode: str  # TODO: should we use a single criterion with multiple attributes to filter by: mode, enrollment date, etc.?

    supported_operators: List[ComparisonOperator] = [
        ComparisonOperator.EQUAL,
        ComparisonOperator.NOT_EQUAL,
    ]
    scopes: List[str] = ["course"]

    def evaluate(self) -> QuerySet:
        """
        Evaluate the criterion.
        """
        # TODO: we should run the tests in the edx-platform environment so enrollment models or APIs are available.


class UserStaffStatusCriterion(BaseCriterionType):
    """A criterion that filters users based on their staff status."""

    updated_by_events = [USER_STAFF_STATUS_CHANGED]
    criterion_type: str = "user_staff_status"
    description: str = (
        "A criterion that filters users based on whether they are staff members or not."
    )

    class ConfigModel(BaseModel):
        """Configuration model for user staff status criterion."""

        model_config = {
            "title": "User Staff Status Criterion Configuration",
            "description": "Configuration for filtering users based on their staff status",
        }

        is_staff: bool = Field(
            description="Whether to filter for staff users (True) or non-staff users (False)",
            examples=[True, False],
        )

    def evaluate(self) -> QuerySet:
        """Evaluate the criterion based on user staff status.

        Args:
            config: Configuration specifying whether to look for staff (True) or non-staff (False) users
            operator: Comparison operator (EQUAL or NOT_EQUAL)
            current_scope: The scope to filter users within
            backend_client: Backend client to get users

        Returns:
            Q object for filtering users
        """
        return self.backend_client.get_users(self.scope).filter(
            is_staff=self.criterion_config.is_staff
        )
