"""
This module is responsible for the base criterion type and the comparison operators.

Here's a high level overview of the module:

- The base criterion type is a class that defines the interface for all criterion types.
- It defines the supported operators, the configuration model, and the evaluation method.
- The comparison operators are used to compare the conditions with the configuration.
- The evaluation method is used to evaluate the criterion.
"""

import logging
from abc import ABC, abstractmethod
from collections import defaultdict
from enum import Enum
from typing import Any, Dict, List, Type

from django.db.models import Q, QuerySet
from openedx_events.tooling import OpenEdxPublicSignal
from pydantic import BaseModel, ValidationError

from openedx_user_groups.backends import BackendClient
from openedx_user_groups.utils import get_scope_type_from_content_type

logger = logging.getLogger(__name__)


class ComparisonOperator(str, Enum):
    """Supported comparison operators for criterion evaluation."""

    # Equality operators
    EQUAL = "="
    NOT_EQUAL = "!="

    # Comparison operators
    GREATER_THAN = ">"
    GREATER_THAN_OR_EQUAL = ">="
    LESS_THAN = "<"
    LESS_THAN_OR_EQUAL = "<="

    # String operators
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"

    # List/Set operators
    IN = "in"
    NOT_IN = "not_in"

    # Existence operators
    EXISTS = "exists"
    NOT_EXISTS = "not_exists"


class BaseCriterionType(ABC):
    """
    Base class for all criterion types.

    Each criterion type must implement this interface to provide validation
    and evaluation logic for specific user group conditions.
    """

    # This is used to map events types to criterion types. For example:
    # {
    #     "org.openedx.learning.user.staff_status.changed.v1": [UserStaffStatusCriterion],
    #     "org.openedx.learning.user.enrollment.changed.v1": [CourseEnrollmentCriterion],
    # }
    _event_to_class_map: Dict[str, List[str]] = defaultdict(list)

    # Must be overridden by subclasses
    criterion_type: str = (
        None  # This matches the criterion_type in the Criterion model, and is used to load the criterion class for evaluation purposes.
    )
    description: str = None

    # Pydantic model for validating configuration. TODO: Should we use attrs instead?
    ConfigModel: Type[BaseModel] = None

    # Supported operators for this criterion type
    # This should be overridden by subclasses
    supported_operators: List[ComparisonOperator] = None

    # As default, all criteria support all scopes.
    scopes: List[str] = ["course", "organization", "instance"]

    # TODO: include these suggestions in the 0002 ADR?

    # TODO: This could be an option to handle estimated selectivity between criteria (0.0 = very restrictive, 1.0 = not restrictive)
    # Lower values will be applied last for better performance. The evaluation engine could handle this by applying the criteria in order of estimated selectivity.
    # estimated_selectivity: float = 0.5

    # TODO: this might not be necessary, we're currently using it for validation purposes when creating a criterion.
    # But we could just validate the config when saving the criterion by using the class methods directly.
    def __init__(
        self,
        criterion_operator: str,
        criterion_config: dict | BaseModel,
        scope,  # Scope model instance - no type hint to avoid circular imports
        backend_client: BackendClient,
    ):
        if isinstance(criterion_config, BaseModel):
            self.criterion_config = (
                criterion_config  # DO not validate if we're passing a pydantic model
            )
        else:
            self.criterion_config = self.validate_config(criterion_config)
        self.criterion_operator = self.validate_operator(criterion_operator)
        scope_type = get_scope_type_from_content_type(
            scope.content_type
        )  # TODO: we need a way of referencing courseoverview without the cognitive overload of understanding what courseoverview is?
        assert (
            scope_type in self.scopes
        ), f"Criterion '{self.criterion_type}' does not support scope type '{scope_type}'. Supported scopes: {self.scopes}"
        self.scope = scope
        self.backend_client = backend_client

    def __init_subclass__(cls, **kwargs):
        """Override to validate the subclass attributes."""
        super().__init_subclass__(**kwargs)
        if cls.criterion_type is None:
            raise ValueError(
                f"Criterion class {cls.__name__} must define a 'criterion_type' attribute"
            )
        if cls.description is None:
            raise ValueError(
                f"Criterion class {cls.__name__} must define a 'description' attribute"
            )
        if cls.ConfigModel is None:
            raise ValueError(
                f"Criterion class {cls.__name__} must define a 'ConfigModel' attribute"
            )

    def validate_config(self, config: Dict[str, Any]) -> BaseModel:
        """
        Validate the configuration using the criterion's Pydantic (or attrs?) model.

        Args:
            config: Raw configuration dictionary

        Returns:
            Validated configuration as Pydantic model instance

        Raises:
            ValidationError: If configuration is invalid
        """
        try:
            return self.ConfigModel(
                **config
            )  # TODO: this is the schematic approach for validating the config.
        except ValidationError as e:
            logger.error(f"Invalid configuration for {self.criterion_type}: {e}")
            raise

    def validate_operator(self, operator: str) -> ComparisonOperator:
        """
        Validate that the operator is supported by this criterion type.

        Args:
            operator: String representation of the operator

        Returns:
            Validated ComparisonOperator enum value

        Raises:
            ValueError: If operator is not supported
        """
        try:
            op = ComparisonOperator(operator)
        except ValueError:
            raise ValueError(f"Unknown operator: {operator}")

        if (
            hasattr(self, "supported_operators")
            and self.supported_operators
            and op not in self.supported_operators
        ):
            raise ValueError(
                f"Operator {operator} not supported by {self.criterion_type}. "
                f"Supported operators: {[op.value for op in self.supported_operators]}"
            )

        return op

    @property
    def config_model(
        self,
    ):  # TODO: this could be used to generate the schema for the configuration. Which can later be used for UI forms?
        """Return the configuration model for this criterion type."""
        return self.ConfigModel

    @abstractmethod
    def evaluate(self) -> QuerySet:  # TODO: for simplicity return a queryset.
        """
        Evaluate the criterion and return a Q object for filtering users.

        Args:
            config: Validated configuration (Pydantic model instance)
            operator: Comparison operator to use
            scope_context: Optional context about the scope (e.g., course_id)

        Returns:
            QuerySet: A queryset of users that match the criterion.
        """
        pass

    def get_updated_by_events(self) -> List[str]:
        """Return the events that trigger an update based on the criterion type.

        Returns:
            List[str]: A list of events that trigger an update to the user groups.
        """
        return self.updated_by_events

    @classmethod
    def get_all_updated_by_events(cls) -> List[OpenEdxPublicSignal]:
        """Return all events that trigger updates across all criterion types.

        This method also populates the _event_to_class_map class attribute that is used to map events to criterion
        types. This is used to determine which criterion types are affected by an event.

        Returns:
            List[OpenEdxPublicSignal]: A list of events that trigger an update to the user groups.
        """
        events = set()
        for subclass in cls.__subclasses__():
            if hasattr(subclass, "updated_by_events"):
                events.update(subclass.updated_by_events)
                for event in subclass.updated_by_events:
                    cls._event_to_class_map[event.event_type].append(
                        subclass.criterion_type
                    )
        return list(events)

    def serialize(self, *args, **kwargs):
        """Return the criterion type, operator and config as a dictionary ready to be saved to the database.

        Args:
            *args: Additional arguments to pass to the model_dump method.
            **kwargs: Additional keyword arguments to pass to the model_dump method.

        Returns:
            dict: A dictionary containing the criterion type, operator and config.
        """
        return {
            "criterion_type": self.criterion_type,
            "criterion_operator": self.criterion_operator,
            "criterion_config": self.criterion_config.model_dump(*args, **kwargs),
        }

    @classmethod
    def get_schema(cls) -> dict:
        """Return the schema for the criterion type.

        Returns:
            dict: A dictionary containing the schema for the criterion type. For example:
            {
                "title": "Manual Criterion Configuration",
                "description": "Configuration for manually specifying users by username or email",
                "properties": {
                    "usernames_or_emails": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of usernames or email addresses to include in the group",
                        "examples": [["user1", "user2@example.com", "user3"]],
                        "minItems": 1
                    }
                },
                "operators": ["in", "not_in"],
                "criterion_description": "A criterion that is used to push a given list of users to a group."
            }
        """
        config_schema = cls.ConfigModel.model_json_schema()

        config_schema_filtered = {
            "title": config_schema.get("title", ""),
            "description": config_schema.get("description", ""),
            "properties": {
                key: value
                for key, value in config_schema.get("properties", {}).items()
                if key in cls.ConfigModel.model_fields
            },
        }

        schema = {
            **config_schema_filtered,
            "operators": (
                [op.value for op in cls.supported_operators]
                if cls.supported_operators
                else []
            ),
            "criterion_description": cls.description,
            "criterion_type": cls.criterion_type,
            "supported_scopes": cls.scopes,
        }

        return schema
