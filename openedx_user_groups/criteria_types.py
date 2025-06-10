"""Module for the criteria types that implement different logic for evaluating the membership of a user group.

Here's a high level overview of the module:
- The criteria types are classes that inherit from the BaseCriterionType class.
- They implement the evaluate method, which is used to evaluate the criterion to determine the lists of users that match the criterion.
- Each criterion implements the evaluate method differently, based on the logic of the criterion. For example, the LastLoginCriterion evaluates the last login of the user,
while the CourseEnrollmentCriterion evaluates the course enrollment of the user.
- These criteria must be registered in the CriterionManager class so they can be loaded dynamically and be used by user groups.
"""

from datetime import timedelta
from typing import Any, Dict, List, Type

from django.db.models import Q
from django.utils import timezone
from pydantic import BaseModel

from openedx_user_groups.backends import BackendClient
from openedx_user_groups.criteria import BaseCriterionType, ComparisonOperator
from openedx_user_groups.models import Scope


class ManualCriterion(BaseCriterionType):
    """
    A criterion that is used to push a given list of users to a group.
    """

    criterion_type: str = "manual"
    description: str = (
        "A criterion that is used to push a given list of users to a group."
    )

    class ConfigModel(BaseModel):
        user_ids: List[str]  # Usernames or emails

    # Supported operators for this criterion type
    supported_operators: List[ComparisonOperator] = [
        ComparisonOperator.IN,
        ComparisonOperator.NOT_IN,
    ]

    def evaluate(
        self,
        current_scope: Scope,
        backend_client: BackendClient = None,
    ) -> Q:  # TODO: Should this be Scope type instead of dict?
        """
        Evaluate the criterion.
        """
        return backend_client.get_users(current_scope).filter(
            id__in=self.criterion_config.user_ids
        )


class CourseEnrollmentCriterion(BaseCriterionType):
    """
    A criterion that is used to evaluate the membership of a user group based on the course enrollment mode of the user.
    """

    criterion_type: str = "course_enrollment"
    description: str = (
        "A criterion that is used to evaluate the membership of a user group based on the course enrollment mode of the user."
    )

    class ConfigModel(BaseModel):
        course_id: str  # TODO: maybe we could use a single criterion with multiple attributes to filter by: mode, enrollment date, etc.

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

    def evaluate(
        self,
        config: ConfigModel,
        operator: ComparisonOperator,
        scope_context: Dict[str, Any] = None,
    ) -> Q:
        """
        Evaluate the criterion.
        """
        # Placeholder implementation for POC
        return Q(id__in=[])


class LastLoginCriterion(BaseCriterionType):
    """
    A criterion that is used to evaluate the membership of a user group based on the last login of the user.
    """

    criterion_type: str = "last_login"
    description: str = (
        "A criterion that is used to evaluate the membership of a user group based on the last login of the user."
    )

    class ConfigModel(BaseModel):
        days: int  # TODO: can we use a single criterion with multiple attributes to filter by: days, country, etc.?

    supported_operators: List[ComparisonOperator] = [
        ComparisonOperator.EQUAL,
        ComparisonOperator.NOT_EQUAL,
        ComparisonOperator.GREATER_THAN,
        ComparisonOperator.GREATER_THAN_OR_EQUAL,
        ComparisonOperator.LESS_THAN,
        ComparisonOperator.LESS_THAN_OR_EQUAL,
    ]

    def evaluate(
        self,
        current_scope: Scope,
        backend_client: BackendClient = None,  # Dependency injection for the backend client
    ) -> Q:
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
        return backend_client.get_users(current_scope).filter(
            **query
        )  # TODO: is it better to use Q objects instead?


class EnrollmentModeCriterion(BaseCriterionType):
    """
    A criterion that is used to evaluate the membership of a user group based on the enrollment mode of the user.
    """

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

    def evaluate(
        self,
        current_scope: Scope,
        backend_client: BackendClient = None,
    ) -> Q:
        """
        Evaluate the criterion.
        """
        # TODO: we should run the tests in the edx-platform environment so enrollment models or APIs are available.


class UserStaffStatusCriterion(BaseCriterionType):
    """
    A criterion that filters users based on their staff status.
    """

    criterion_type: str = "user_staff_status"
    description: str = (
        "A criterion that filters users based on whether they are staff members or not."
    )

    class ConfigModel(BaseModel):
        is_staff: bool  # True to filter for staff users, False for non-staff users

    supported_operators: List[ComparisonOperator] = (
        [  # TODO: I don't think we need to support any operator. Maybe a simple is true?
            # ComparisonOperator.EQUAL,
            # ComparisonOperator.NOT_EQUAL,
        ]
    )

    def evaluate(
        self,
        current_scope: Scope,
        backend_client: BackendClient = None,
    ) -> Q:
        """
        Evaluate the criterion based on user staff status.

        Args:
            config: Configuration specifying whether to look for staff (True) or non-staff (False) users
            operator: Comparison operator (EQUAL or NOT_EQUAL)
            current_scope: The scope to filter users within
            backend_client: Backend client to get users

        Returns:
            Q object for filtering users
        """
        return backend_client.get_users(current_scope).filter(
            is_staff=self.criterion_config.is_staff
        )
