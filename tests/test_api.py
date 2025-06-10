"""Test Suite for the User Group interface (api.py) that could be used by other modules.

This test suite is only for POC purposes, so it won't follow the best practices for testing,
this module could be refactored later on.

This test suite will be used to test the public / private API of the User Group module.
"""

import factory
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from datetime import timedelta

from openedx_user_groups.api import *
from openedx_user_groups.models import UserGroup, Scope, Criterion


User = get_user_model()


class CourseFactory(factory.Factory):
    """Factory for creating Course-like objects for testing.

    Since we don't want to create a real Course model, this factory
    generates dict objects that simulate course data.
    """

    class Meta:
        model = dict  # Use a dict to simulate a course object

    course_id = factory.Sequence(lambda n: f"course-v1:edX+Demo{n}+Course")
    name = factory.Faker("sentence", nb_words=3)
    description = factory.Faker("text", max_nb_chars=200)
    id = factory.Sequence(lambda n: n)


class UserFactory(factory.django.DjangoModelFactory):
    """Factory for creating User instances."""

    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"user_{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")


class ScopeFactory(factory.django.DjangoModelFactory):
    """Factory for creating Scope instances."""

    class Meta:
        model = Scope

    name = factory.Faker("sentence", nb_words=3)
    description = factory.Faker("text", max_nb_chars=200)
    # Use User model's ContentType as a default since it exists in test DB
    content_type = factory.LazyFunction(lambda: ContentType.objects.get_for_model(User))
    object_id = factory.Sequence(lambda n: n)


class UserGroupFactory(factory.django.DjangoModelFactory):
    """Factory for creating UserGroup instances."""

    class Meta:
        model = UserGroup

    name = factory.Faker("sentence", nb_words=2)
    description = factory.Faker("text", max_nb_chars=200)
    enabled = True
    scope = factory.SubFactory(ScopeFactory)


class CriterionFactory(factory.django.DjangoModelFactory):
    """Factory for creating Criterion instances."""

    class Meta:
        model = Criterion


class LastLoginCriterionFactory(CriterionFactory):
    """Factory for creating LastLoginCriterion instances."""

    criterion_type = "last_login"
    criterion_operator = ">"  # Login date is greater than 1 day ago
    criterion_config = factory.Dict({"days": 1})


class EnrollmentModeCriterionFactory(CriterionFactory):
    """Factory for creating EnrollmentModeCriterion instances."""

    criterion_type = "enrollment_mode"
    criterion_operator = "="
    criterion_config = factory.Dict({"mode": "honor"})


class UserStaffStatusCriterionFactory(CriterionFactory):
    """Factory for creating UserStaffStatusCriterion instances."""

    criterion_type = "user_staff_status"
    criterion_operator = "="
    criterion_config = factory.Dict({"is_staff": False})  # Filter for non-staff users


class UserGroupAPITestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        """Set up test data that will be reused across all test methods."""
        cls.test_course = CourseFactory()
        cls.course_content_type = ContentType.objects.get_for_model(User)
        cls.test_scope = ScopeFactory(
            name=cls.test_course["name"],
            content_type=cls.course_content_type,
            object_id=cls.test_course["id"],
        )
        cls.test_user_group_data = UserGroupFactory.build(name="At Risk Students")
        cls.last_login_criterion = LastLoginCriterionFactory.build()
        cls.enrollment_mode_criterion = EnrollmentModeCriterionFactory.build()
        cls.user_staff_status_criterion = UserStaffStatusCriterionFactory.build()
        cls.scope_context = {
            "name": cls.test_course["name"],
            "content_object": {
                "content_type": cls.course_content_type,
                "object_id": cls.test_course["id"],
            },
        }

    def test_create_group_with_no_criteria(self):
        """Test that a group can be created with no criteria associated.

        Expected Results:
        - The group is created successfully.
        - The group has no criteria associated.
        - The group has the correct name, description, and scope.
        - The group has no members.
        - The group is enabled.
        """
        user_group, scope = get_or_create_group_and_scope(
            name=self.test_user_group_data.name,
            description=self.test_user_group_data.description,
            scope_context=self.scope_context,
        )

        assert user_group is not None
        assert user_group.name == self.test_user_group_data.name
        assert user_group.description == self.test_user_group_data.description
        assert scope.name == self.test_scope.name
        assert user_group.criteria.count() == 0

    def test_associate_multiple_groups_with_same_scope(self):
        """Test that multiple groups can be associated with the same scope.

        Expected Results:
        - The groups are created successfully.
        - The groups have the correct name, description, and scope.
        - The groups are associated with the same scope.
        """
        user_group_1, scope_1 = get_or_create_group_and_scope(
            name=f"{self.test_user_group_data.name}_1",
            description=self.test_user_group_data.description,
            scope_context=self.scope_context,
        )
        user_group_2, scope_2 = get_or_create_group_and_scope(
            name=f"{self.test_user_group_data.name}_2",
            description=self.test_user_group_data.description,
            scope_context=self.scope_context,
        )

        assert scope_1.name == self.test_scope.name
        assert scope_2.name == self.test_scope.name
        assert scope_1.name == scope_2.name

    def test_create_group_with_single_criterion(self):
        """Test that a group can be created with a single criterion.

        Expected Results:
        - The group is created successfully.
        - The group has the correct name, description, and scope.
        - The group has the correct criterion.
        """
        user_group = create_group_with_criteria(
            name=self.test_user_group_data.name,
            description=self.test_user_group_data.description,
            scope_context=self.scope_context,
            criterion_data=[
                {
                    "criterion_type": self.last_login_criterion.criterion_type,
                    "criterion_operator": self.last_login_criterion.criterion_operator,
                    "criterion_config": self.last_login_criterion.criterion_config,
                }
            ],
        )

        assert user_group is not None
        assert user_group.criteria.count() == 1

    def test_create_group_with_multiple_criteria(self):
        """Test that a group can be created with multiple criteria.

        Expected Results:
        - The group is created successfully.
        - The group has the correct name, description, and scope.
        - The group has the correct criteria.

        In this case the criteria would be:
        1. Last login in the last 1 day
        2. Enrolled with honor mode
        """
        user_group = create_group_with_criteria(
            name=self.test_user_group_data.name,
            description=self.test_user_group_data.description,
            scope_context=self.scope_context,
            criterion_data=[
                {
                    "criterion_type": self.last_login_criterion.criterion_type,
                    "criterion_operator": self.last_login_criterion.criterion_operator,
                    "criterion_config": self.last_login_criterion.criterion_config,
                },
                {
                    "criterion_type": self.enrollment_mode_criterion.criterion_type,
                    "criterion_operator": self.enrollment_mode_criterion.criterion_operator,
                    "criterion_config": self.enrollment_mode_criterion.criterion_config,
                },
            ],
        )
        assert user_group is not None
        assert user_group.criteria.count() == 2
        assert user_group.criteria.filter(
            criterion_type=self.last_login_criterion.criterion_type
        ).exists()
        assert user_group.criteria.filter(
            criterion_type=self.enrollment_mode_criterion.criterion_type
        ).exists()

    def test_create_group_with_mismatched_criteria_scope(self):
        """Test that a group can't be created with criteria that don't match the group's scope.

        Expected Results:
        - The group is not created.
        - An exception is raised.
        """
        pass

    def test_create_group_with_criteria_and_evaluate_membership(self):
        """Test that a group can be created with criteria and immediatly evaluated for membership.

        Expected Results:
        - The group is created successfully.
        - The group has the correct name, description, and scope.
        - The group has the correct criteria.
        - The group has the correct members.

        Criteria:
        1. Last login GREATER_THAN 1 day ago (meaning older than 1 day)
        2. User is non-staff (is_staff = False)

        Expected match: user_old_login_non_staff (2 days ago, non-staff)
        """
        # Create users with different characteristics for testing
        # Clean up any existing users
        User.objects.all().delete()

        user_old_login_non_staff = UserFactory(
            username="user_old_login_non_staff",
            last_login=timezone.now() - timedelta(days=2),  # 2 days ago (> 1 day ago)
            is_staff=False,  # non-staff
        )
        user_recent_login_staff = UserFactory(
            username="user_recent_login_staff",
            last_login=timezone.now() - timedelta(hours=1),  # 1 hour ago (< 1 day ago)
            is_staff=True,  # staff
        )
        user_old_login_staff = UserFactory(
            username="user_old_login_staff",
            last_login=timezone.now() - timedelta(days=3),  # 3 days ago (> 1 day ago)
            is_staff=True,  # staff (fails is_staff=False criterion)
        )

        # Create a group with criteria (last_login and staff_status)
        user_group = create_group_with_criteria_and_evaluate_membership(
            name=self.test_user_group_data.name,
            description=self.test_user_group_data.description,
            scope_context=self.scope_context,
            criterion_data=[
                {
                    "criterion_type": self.last_login_criterion.criterion_type,
                    "criterion_operator": self.last_login_criterion.criterion_operator,
                    "criterion_config": self.last_login_criterion.criterion_config,
                },
                {
                    "criterion_type": self.user_staff_status_criterion.criterion_type,
                    "criterion_operator": self.user_staff_status_criterion.criterion_operator,
                    "criterion_config": self.user_staff_status_criterion.criterion_config,
                },
            ],
        )
        assert user_group is not None
        assert user_group.criteria.count() == 2
        assert user_group.users.count() == 1
        # Should match user_old_login_non_staff (old login AND non-staff)
        assert user_group.users.first() == user_old_login_non_staff

    def test_evaluate_membership_for_multiple_groups(self):
        """Test that the membership of multiple groups can be evaluated and updated.

        Expected Results:
        - The groups are evaluated successfully.
        - The groups have the correct members.
        """
        # Clean up any existing users
        User.objects.all().delete()

        # Create users with different characteristics for testing
        user_old_login_non_staff = UserFactory(
            username="user_old_login_non_staff",
            last_login=timezone.now() - timedelta(days=2),  # 2 days ago (> 1 day ago)
            is_staff=False,  # non-staff
        )

        # Create a groups with criteria
        groups = [
            create_group_with_criteria(
                name=f"{self.test_user_group_data.name}_{i}",
                description=self.test_user_group_data.description,
                scope_context=self.scope_context,
                criterion_data=[
                    {
                        "criterion_type": self.last_login_criterion.criterion_type,
                        "criterion_operator": self.last_login_criterion.criterion_operator,
                        "criterion_config": self.last_login_criterion.criterion_config,
                    }
                ],
            )
            for i in range(2)
        ]
        assert len(groups) == 2

        # Evaluate the membership of the groups
        evaluate_and_update_membership_for_multiple_groups(
            [group.id for group in groups]
        )

        assert groups[0].users.count() == 1
        assert groups[1].users.count() == 1
