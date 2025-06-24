"""Test Suite for the User Group tasks.

This test suite covers all tasks defined in tasks.py.
"""

from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth import get_user_model

from openedx_user_groups.tasks import orchestrate_user_groups_updates_based_on_events
from openedx_user_groups.handlers import handle_user_group_update
from openedx_user_groups.criteria import BaseCriterionType
from openedx_user_groups.api import *
from tests.factories import *

from openedx_events.learning.data import UserPersonalData
from openedx_user_groups.events import USER_STAFF_STATUS_CHANGED, UserDataExtended

User = get_user_model()


class TestOrchestrateUserGroupsUpdatesBasedOnEvents(TestCase):
    """Test the orchestrate_user_groups_updates_based_on_events task logic."""

    @classmethod
    def setUpTestData(cls):
        """Set up the test environment."""
        for event in BaseCriterionType.get_all_updated_by_events():
            event.connect(handle_user_group_update)
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
        cls.user_old_login_non_staff = UserFactory(
            username="user_old_login_non_staff",
            last_login=timezone.now() - timedelta(days=2),  # 2 days ago (> 1 day ago)
            is_staff=False,  # non-staff
        )
        cls.user_old_login_non_staff_2 = UserFactory(
            username="user_old_login_non_staff_2",
            last_login=timezone.now() - timedelta(days=2),  # 2 days ago (> 1 day ago)
            is_staff=False,  # non-staff
        )
        cls.user_recent_login_staff = UserFactory(
            username="user_recent_login_staff",
            last_login=timezone.now() - timedelta(hours=1),  # 1 hour ago (< 1 day ago)
            is_staff=True,  # staff
        )
        cls.user_old_login_staff = UserFactory(
            username="user_old_login_staff",
            last_login=timezone.now() - timedelta(days=3),  # 3 days ago (> 1 day ago)
            is_staff=True,  # staff (fails is_staff=False criterion)
        )
        cls.user_old_login_non_staff_group = create_group_with_criteria(  # Returns user_old_login_non_staff and user_old_login_non_staff_2
            name="Old Login Non Staff Group",
            description="Old Login Non Staff Group",
            scope_context=cls.scope_context,
            criterion_data=[
                {
                    "criterion_type": cls.last_login_criterion.criterion_type,
                    "criterion_operator": cls.last_login_criterion.criterion_operator,
                    "criterion_config": cls.last_login_criterion.criterion_config,
                },
                {
                    "criterion_type": cls.user_staff_status_criterion.criterion_type,
                    "criterion_operator": cls.user_staff_status_criterion.criterion_operator,
                    "criterion_config": cls.user_staff_status_criterion.criterion_config,
                },
            ],
        )
        # TODO: during tests I found that I could create duplicated groups (same name, same scope) need to check it
        # And only the last one is being created no error or warning is raised
        cls.user_non_staff_status_group = create_group_with_criteria(  # Returns user_old_login_staff, user_old_login_non_staff, user_old_login_non_staff_2
            name="Non Staff Status Group",
            description="Non Staff Status Group",
            scope_context=cls.scope_context,
            criterion_data=[
                {
                    "criterion_type": cls.user_staff_status_criterion.criterion_type,
                    "criterion_operator": cls.user_staff_status_criterion.criterion_operator,
                    "criterion_config": cls.user_staff_status_criterion.criterion_config,
                },
            ],
        )
        evaluate_and_update_membership_for_multiple_groups(
            [cls.user_old_login_non_staff_group.id, cls.user_non_staff_status_group.id]
        )
        cls.new_user_non_staff = UserFactory(  # Create user after evaluation
            username="new_user_non_staff",
            last_login=timezone.now() - timedelta(hours=1),  # 1 hour ago (< 1 day ago)
            is_staff=False,  # staff
        )

    def test_orchestrate_updates_with_user_not_in_any_group(self):
        """Test the event-based update for a user that is not in any group.

        Expected Results:
        - Since the user doesn't belong to any group, then all criteria type affected by the event should be
        updated.
        """
        USER_STAFF_STATUS_CHANGED.send_event(
            user=UserDataExtended(
                is_staff=self.new_user_non_staff.is_staff,
                pii=UserPersonalData(
                    username=self.new_user_non_staff.username,
                    email=self.new_user_non_staff.email,
                    name=f"{self.new_user_non_staff.first_name} {self.new_user_non_staff.last_name}",
                ),
                id=self.new_user_non_staff.id,
                is_active=self.new_user_non_staff.is_active,
            ),
        )
        self.assertEqual(get_groups_for_user(self.new_user_non_staff.id).count(), 1)

    def test_orchestrate_updates_with_user_in_multiple_groups(self):
        """Test the event-based update for a user that is in multiple groups.

        Expected Results:
        - Since the user belongs to a single group, then the group that is configured with the criteria types should be updated.
        - Also the other groups with the same criteria type should be updated.
        """
        staff_user_group = create_group_with_criteria(
            name="Staff User Group",
            description="Staff User Group",
            scope_context=self.scope_context,
            criterion_data=[
                {
                    "criterion_type": self.user_staff_status_criterion.criterion_type,
                    "criterion_operator": self.user_staff_status_criterion.criterion_operator,
                    "criterion_config": {"is_staff": True},
                },
            ],
        )
        evaluate_and_update_membership_for_multiple_groups([staff_user_group.id])
        assert self.user_old_login_non_staff not in staff_user_group.users.all()
        assert (
            self.user_old_login_non_staff
            in self.user_old_login_non_staff_group.users.all()
        )

        # Update the user to be staff before sending the event
        self.user_old_login_non_staff.is_staff = True
        self.user_old_login_non_staff.save()

        USER_STAFF_STATUS_CHANGED.send_event(
            user=UserDataExtended(
                is_staff=True,
                pii=UserPersonalData(
                    username=self.user_old_login_non_staff.username,
                    email=self.user_old_login_non_staff.email,
                    name=f"{self.user_old_login_non_staff.first_name} {self.user_old_login_non_staff.last_name}",
                ),
                id=self.user_old_login_non_staff.id,
                is_active=self.user_old_login_non_staff.is_active,
            )
        )
        assert (
            self.user_old_login_non_staff
            not in self.user_old_login_non_staff_group.users.all()
        )
        assert self.user_old_login_non_staff in staff_user_group.users.all()
        self.user_old_login_non_staff.is_staff = False
        self.user_old_login_non_staff.save()

    def test_orchestrate_updates_when_there_is_no_change_in_membership_state(self):
        """Test when the event-based update doesn't change the membership state.

        Expected Results:
        - Since the update doesn't affect the membership state, then no groups should be updated.
        """
        assert (
            self.user_old_login_non_staff
            in self.user_old_login_non_staff_group.users.all()
        )
        assert (
            self.user_old_login_non_staff
            in self.user_non_staff_status_group.users.all()
        )
        USER_STAFF_STATUS_CHANGED.send_event(
            user=UserDataExtended(
                is_staff=self.user_old_login_non_staff.is_staff,  # No change in membership state
                pii=UserPersonalData(
                    username=f"{self.user_old_login_non_staff.username}_2",  # Changed username, but it doesn't affect the membership state
                    email=f"{self.user_old_login_non_staff.email}_2",
                    name=f"{self.user_old_login_non_staff.first_name}_2 {self.user_old_login_non_staff.last_name}_2",
                ),
                id=self.user_old_login_non_staff.id,
                is_active=self.user_old_login_non_staff.is_active,
            )
        )
        assert (
            self.user_old_login_non_staff
            in self.user_old_login_non_staff_group.users.all()
        )
        assert (
            self.user_old_login_non_staff
            in self.user_non_staff_status_group.users.all()
        )
