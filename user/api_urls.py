from django.urls import path, include

import user.api_views

urlpatterns = [

    path('<int:pk>/', user.api_views.UserViewSet.as_view()),
    path('<int:pk>/update/', user.api_views.UserViewSetUpdate.as_view()),

    path('<int:pk>/language/', user.api_views.LanguageViewSet.as_view()),
    path('<int:pk>/language/update', user.api_views.UpdateLanguageView.as_view()),
    
    path('registration/register/', user.api_views.RegisterView.as_view(),),
    path('registration/verify-email/', user.api_views.VerifyEmailView,),
    path('registration/verify-registration/', user.api_views.VerifyRegistrationView.as_view(),),
    path('registration/send-reset-password-link/',user.api_views.SendResetPasswordLinkView.as_view()),
    path('registration/reset-password/', user.api_views.ResetPasswordView.as_view(),),
    path('unregister/', user.api_views.UserViewUnregister.as_view(),),

    path('', include("django.contrib.auth.urls")),
]
