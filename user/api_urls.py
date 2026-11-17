from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import api_views

router = DefaultRouter()
router.register(r'profile', api_views.UserViewSet, basename='user-profile')

urlpatterns = [
    path('', include(router.urls)),

    # Pas d'inscription libre : les comptes sont créés dans l'admin Django, le mot de passe se choisit via ce lien
    path('registration/send-reset-password-link/', api_views.SendResetPasswordLinkView.as_view()),
    path('registration/reset-password/', api_views.ResetPasswordView.as_view()),
    
    path('', include("django.contrib.auth.urls")),
]