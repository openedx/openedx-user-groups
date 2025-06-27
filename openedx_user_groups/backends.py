"""Module for backend clients that the criteria can use to evaluate their conditions and
return users for the group.
"""

from django.contrib.auth import get_user_model
from django.db.models import QuerySet

# Scope import removed to avoid circular import - using duck typing instead

User = get_user_model()


class BackendClient:
    """Base class for backend clients."""


class DjangoORMBackendClient(BackendClient):
    """Backend client that uses Django ORM get data for criteria evaluation.

    All these methods return querysets of users for the given scope, augmented with the
    relevant data for the criterion.

    TODO: how can I always return a queryset of objects alongside users? I don't know if this is possible.

    Course vs Organization
    - Course:
        - get_enrollments (all students in the course)
        - get_users (all users in the course)
        - get_grade (all grades for the course)
    - Organization:
        - get_enrollments (all students in the organization)
        - get_users (all users in the organization)
    """

    @staticmethod
    def get_enrollments(scope) -> QuerySet:  # scope: Scope model instance
        """Provide an interface to get all user enrollments for a given scope.

        Args:
            scope (Scope): The scope to get the enrollments for.

        Returns:
            QuerySet: A queryset of user enrollments for the given scope.
        """
        # TODO: need an API to get enrollment objects for a given course. Currently, there is no way
        # of implementing unittests for this without edx-platform. Can be executed as part of the
        # edx-platform tests though.
        from common.djangoapps.student.models import CourseEnrollment

        return CourseEnrollment.objects.filter(
            course_id=scope.object_id
        )  # TODO: this could be a way of managing external imports. Can we standardize this?

    @staticmethod
    def get_users(scope) -> QuerySet:  # scope: Scope model instance
        """Provide an interface to get all users for a given scope.

        For simplicity reasons, we'll consider all users in the current instance. The idea would be
        to filter users depending on whether they're enrolled in a course in the org or in a course
        itself, but since we don't have an API to access this data, we'll just return all users in the instance.
        """
        return User.objects.all().exclude(is_staff=True, is_superuser=True)

    @staticmethod
    def get_grade(scope) -> QuerySet:  # scope: Scope model instance
        """Provide an interface to get all grades for a given scope.

        This method should be implemented by the backend client. Use existent API methods to get the data for the scope.
        """
        pass

    @staticmethod
    def get_course_progress(scope) -> QuerySet:  # scope: Scope model instance
        """Provide an interface to get all course progress for a given scope.

        This method should be implemented by the backend client. Use existent API methods to get the data for the scope.
        """
        pass


class SupersetBackendClient(BackendClient):
    """Backend client that uses Superset to get data for criteria evaluation.

    This backend client is used to get data for the criteria evaluation from Superset.
    """

    # TODO: find a good example for this backend client. I don't know if there is an easy way of
    # Implementing unittests for this since we'd need an Aspects instance for it to work?
    # Maybe mocking the communication with Superset?
