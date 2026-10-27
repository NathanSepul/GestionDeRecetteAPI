from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .api_views import ListeCourseViewSet

router = DefaultRouter()
router.register(r'', ListeCourseViewSet, basename='liste-course')

urlpatterns = [
    path('', include(router.urls)),
]
