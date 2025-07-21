from django.urls import path

import typeRecette.api_views


urlpatterns = [

    path('',typeRecette.api_views.TypeRecetteListAPIView.as_view()),
    path('create/',typeRecette.api_views.TypeRecetteCreateAPIView.as_view()),
    path('<int:pk>/update/',typeRecette.api_views.TypeRecetteUpdateAPIView.as_view()),
    path('<int:pk>/remove/',typeRecette.api_views.TypeRecetteDeleteAPIView.as_view()),


]