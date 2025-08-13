from django.urls import path

import recette.api_views


urlpatterns = [

    path('',recette.api_views.RecetteListAPIView.as_view()),
    path('lite/',recette.api_views.RecetteListLiteAPIView.as_view()),
    path('<int:pk>/', recette.api_views.RecetteRetrieveAPIView.as_view()),
    path('create/', recette.api_views.RecetteCreateAPIView.as_view()),
    path('<int:pk>/update/',recette.api_views.RecetteUpdateAPIView.as_view()),
    path('<int:pk>/remove/',recette.api_views.RecetteDeleteAPIView.as_view()),
    path('<int:pk>/ingredient/reorder/<int:pkIngredient>/', recette.api_views.IngredientReorderAPIView.as_view()),

    path('<int:pk>/ingredient/', recette.api_views.IngredientRetrieveAPIView.as_view()),
    path('ingredient/create/', recette.api_views.IngredientCreateAPIView.as_view()),
    path('ingredient/<int:pk>/update/', recette.api_views.IngredientUpdateAPIView.as_view()),
    path('ingredient/<int:pk>/remove/',recette.api_views.IngredientDeleteAPIView.as_view()),


    path('<int:pk>/preparation/', recette.api_views.PreparationRetrieveAPIView.as_view()),
    path('preparation/create/', recette.api_views.PreparationCreateAPIView.as_view()),
    path('preparation/<int:pk>/update/', recette.api_views.PreparationUpdateAPIView.as_view()),
    path('preparation/<int:pk>/remove/',recette.api_views.PreparationDeleteAPIView.as_view()),

]