"""
URLs for openedx_user_groups.
"""

from django.urls import include, re_path
from rest_framework.routers import DefaultRouter

from openedx_user_groups.views import AvailableCriteriaView, UserGroupViewSet

router = DefaultRouter()
router.register(r"user-groups", UserGroupViewSet, basename="usergroup")

urlpatterns = [
    re_path(
        r"^available-criteria/$",
        AvailableCriteriaView.as_view(),
        name="available-criteria",
    ),
    re_path(r"^", include(router.urls)),
]
