from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import api_views

router = DefaultRouter()
# Le router gère : / , /{id}/ , /{id}/follow/ , /{id}/language/
router.register(r'profiles', api_views.UserViewSet, basename='user-profile')

urlpatterns = [
    path('', include(router.urls)),

    path('registration/register/', api_views.RegisterView.as_view()),
    path('registration/verify-email/', api_views.VerifyEmailView),
    path('registration/verify-registration/', api_views.VerifyRegistrationView.as_view()),
    path('registration/send-reset-password-link/', api_views.SendResetPasswordLinkView.as_view()),
    path('registration/reset-password/', api_views.ResetPasswordView.as_view()),
    
    path('', include("django.contrib.auth.urls")),
]