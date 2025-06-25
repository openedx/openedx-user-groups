"""Factories for creating test data."""

import factory
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
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


class ManualCriterionFactory(CriterionFactory):
    """Factory for creating ManualCriterion instances."""

    criterion_type = "manual"
    criterion_operator = "in"
