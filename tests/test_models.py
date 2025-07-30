"""Test Suite for the User Group models.

This test suite covers all model methods, properties, and behaviors defined in models.py.
"""

import factory
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase
from organizations.models import Organization

from openedx_user_groups.manager import CriterionManager
from openedx_user_groups.models import Criterion, Scope, UserGroup
from tests.factories import (
    UserFactory,
    UserGroupFactory,
)

User = get_user_model()


class CourseFactory(factory.Factory):
    """Factory for creating simple course data objects for testing."""

    class Meta:
        model = dict

    course_id = factory.Sequence(lambda n: f"course-v1:edX+Demo{n}+Course")
    name = factory.Faker("sentence", nb_words=3)
    description = factory.Faker("text", max_nb_chars=200)
    id = factory.Sequence(lambda n: n)


class TestUserGroupMethods(TestCase):
    """Test UserGroup model methods and properties."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data for UserGroup tests."""
        # Create course data using the factory
        cls.test_course = CourseFactory()

        # Create a test organization instead of using User model
        cls.test_organization = Organization.objects.create(
            name="Test Organization",
            short_name="TestOrg",
            description="A test organization for user groups",
        )
        cls.organization_content_type = ContentType.objects.get_for_model(Organization)

        cls.scope = Scope.objects.create(
            name="Test Organization Scope",
            description="Scope for the test organization",
            content_type=cls.organization_content_type,
            object_id=cls.test_organization.id,
        )

        cls.user_group = UserGroup.objects.create(
            name="Test Group", description="A test group", scope=cls.scope
        )

    def test_user_group_str_method(self):
        """Test UserGroup __str__ method returns the name.

        Expected Results:
        - The __str__ method returns the name of the group.
        """
        assert str(self.user_group) == "Test Group"

    def test_user_group_save_prevents_scope_change(self):
        """Test that UserGroup.save() prevents changing scope of existing group.

        Expected Results:
        - The group is not saved.
        - An exception is raised.
        """
        # Create another organization for the new scope
        another_organization = Organization.objects.create(
            name="Another Test Organization",
            short_name="AnotherOrg",
            description="Another test organization",
        )
        new_scope = Scope.objects.create(
            name="New Scope",
            description="Another scope",
            content_type=self.organization_content_type,
            object_id=another_organization.id,
        )

        self.user_group.scope = new_scope

        with self.assertRaises(ValueError) as context:
            self.user_group.save()

        assert "Cannot change the scope of an existing user group" in str(
            context.exception
        )

    def test_user_group_criteria_classes_method(self):
        """Test UserGroup criteria_classes method returns criterion types.

        Expected Results:
        - The method returns a list of criterion types classes associated with the user group.
        """
        user_group_with_criteria = UserGroup.objects.create(
            name="Test Group with Criteria",
            scope=self.scope,
        )
        Criterion.objects.create(
            user_group=user_group_with_criteria,
            criterion_type="last_login",
            criterion_operator=">=",
            criterion_config={"days": 5},
        )

        criterion_templates = user_group_with_criteria.criteria_templates()
        assert len(criterion_templates) == 1
        assert criterion_templates[0] is not None
        assert criterion_templates[0].criterion_type == "last_login"


class TestCriterionMethods(TestCase):
    """Test Criterion model methods and properties."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data for Criterion tests."""
        # Create a test organization
        cls.test_organization = Organization.objects.create(
            name="Test Organization",
            short_name="TestOrg",
            description="A test organization for user groups",
        )
        cls.organization_content_type = ContentType.objects.get_for_model(Organization)

        cls.scope = Scope.objects.create(
            name="Test Organization Scope",
            content_type=cls.organization_content_type,
            object_id=cls.test_organization.id,
        )
        cls.user_group = UserGroup.objects.create(name="Test Group", scope=cls.scope)
        cls.criterion = Criterion.objects.create(
            user_group=cls.user_group,
            criterion_type="last_login",
            criterion_operator=">=",
            criterion_config={"days": 5},
        )

    def test_criterion_str_method(self):
        """Test Criterion __str__ method."""
        expected = "last_login - Test Group"
        assert str(self.criterion) == expected

    def test_criterion_type_property(self):
        """Test Criterion criterion_type property."""
        criterion_type = self.criterion.criterion_type_template
        assert criterion_type is not None
        assert criterion_type.criterion_type == "last_login"

    def test_get_available_criterion_types(self):
        """Test that the get_available_criterion_types method returns the correct criterion types.

        Expected Results:
        - The method returns a list of criterion types classes available for the entire system.
        """
        available_types = Criterion.available_criterion_types()
        assert CriterionManager.get_criterion_types() == available_types

    def test_criterion_type_validation(self):
        """Test that invalid criterion types are rejected."""
        # Test that invalid criterion type raises ValidationError
        invalid_criterion = Criterion(
            user_group=self.user_group,
            criterion_type="invalid_type_that_does_not_exist",
            criterion_operator="=",
        )

        # This should raise a ValidationError when full_clean() is called
        with self.assertRaises(ValidationError) as context:
            invalid_criterion.full_clean()

        # Check that the error is about criterion_type
        assert "criterion_type" in str(
            context.exception
        ) or "is not a valid criterion type" in str(context.exception)


class TestModelConstraints(TestCase):
    """Test model constraints and unique together constraints.

    We're not testing that Django works, but that the design of the models is correct.
    """

    @classmethod
    def setUpTestData(cls):
        """Set up test data for constraint tests."""
        # Create a test organization
        cls.test_organization = Organization.objects.create(
            name="Test Organization",
            short_name="TestOrg",
            description="A test organization for user groups",
        )
        cls.organization_content_type = ContentType.objects.get_for_model(Organization)

        cls.scope = Scope.objects.create(
            name="Test Organization Scope",
            content_type=cls.organization_content_type,
            object_id=cls.test_organization.id,
        )
        cls.user_group = UserGroup.objects.create(name="Test Group", scope=cls.scope)

    def test_user_group_unique_name_per_scope(self):
        """Test that UserGroup name must be unique within a scope."""
        # This should work fine
        UserGroup.objects.create(name="Unique Name", scope=self.scope)

        # This should raise an IntegrityError due to unique_together constraint
        with self.assertRaises(IntegrityError):
            UserGroup.objects.create(name="Unique Name", scope=self.scope)

    def test_user_group_same_name_different_scope(self):
        """Test that UserGroup can have same name in different scopes."""
        # Create another course data and scope
        another_organization = Organization.objects.create(
            name="Another Test Organization",
            short_name="AnotherOrg",
            description="Another test organization",
        )
        another_scope = Scope.objects.create(
            name="Another Scope",
            content_type=self.organization_content_type,
            object_id=another_organization.id,
        )

        # This should work fine - same name but different scope
        another_group = UserGroup.objects.create(
            name="Test Group",  # Same name as the one in setUpTestData
            scope=another_scope,
        )

        assert another_group.name == self.user_group.name
        assert another_group.scope != self.user_group.scope

    def test_criterion_multiple_same_type_per_group(self):
        """Test that multiple criteria of the same type can exist in a user group."""
        # This should work fine
        criterion1 = Criterion.objects.create(
            criterion_type="last_login",
            criterion_operator=">=",
            criterion_config={"days": 5},
            user_group=self.user_group,
        )

        # This should also work fine - multiple criteria of same type are allowed
        criterion2 = Criterion.objects.create(
            criterion_type="last_login",
            criterion_operator="<=",
            criterion_config={"days": 10},
            user_group=self.user_group,
        )

        # Both criteria should exist
        assert (
            Criterion.objects.filter(
                user_group=self.user_group, criterion_type="last_login"
            ).count()
            == 2
        )
