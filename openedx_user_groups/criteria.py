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
from enum import Enum
from typing import Any, Dict, List, Type

from django.db.models import Q, QuerySet
from pydantic import BaseModel, ValidationError

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
        criterion_config: dict,
    ):
        self.criterion_operator = self.validate_operator(criterion_operator)
        self.criterion_config = self.validate_config(criterion_config)

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
        if cls.supported_operators is None:
            raise ValueError(
                f"Criterion class {cls.__name__} must define a 'supported_operators' attribute"
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

        if op not in self.supported_operators:
            raise ValueError(
                f"Operator {operator} not supported by {self.criterion_type}. "
                f"Supported operators: {[op.value for op in self.supported_operators]}"
            )

        return op

    @property
    def supported_operators(self):
        """Return the supported operators for this criterion type."""
        return self.supported_operators

    @property
    def config_model(
        self,
    ):  # TODO: this could be used to generate the schema for the configuration. Which can later be used for UI forms?
        """Return the configuration model for this criterion type."""
        return self.ConfigModel

    @abstractmethod
    def evaluate(
        self,
        config: BaseModel,
        operator: ComparisonOperator,
        scope_context: Dict[str, Any] = None,
    ) -> QuerySet:  # TODO: for simplicity return a queryset.
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
