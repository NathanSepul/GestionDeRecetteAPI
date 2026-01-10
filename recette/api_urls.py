from django.urls import path

import recette.api_views


urlpatterns = [

    path('',recette.api_views.RecetteListAPIView.as_view()),
    path('singlePage/',recette.api_views.RecetteSinglePageAPIView.as_view()),
    path('create/', recette.api_views.RecetteCreateAPIView.as_view()),
    path('<int:pk>/update/',recette.api_views.RecetteUpdateAPIView.as_view()),
    path('<int:pk>/remove/',recette.api_views.RecetteDeleteAPIView.as_view()),
    path('<int:pk>/ingredient/reorder/<int:pkIngredient>/', recette.api_views.IngredientReorderAPIView.as_view()),
    path('<int:pk>/preparation/reorder/<int:pkPreparation>/', recette.api_views.PreparationReorderAPIView.as_view()),

    path('convert',recette.api_views.convert.as_view()),

    path('produit/',recette.api_views.ProduitListAPIView.as_view()),
    path('unite/',recette.api_views.UniteListAPIView.as_view()),

    path('<int:pk>/ingredient/', recette.api_views.IngredientRetrieveAPIView.as_view()),
    path('ingredient/create/', recette.api_views.IngredientCreateAPIView.as_view()),
    path('ingredient/<int:pk>/update/', recette.api_views.IngredientUpdateAPIView.as_view()),
    path('ingredient/<int:pk>/remove/',recette.api_views.IngredientDeleteAPIView.as_view()),


    path('<int:pk>/preparation/', recette.api_views.PreparationRetrieveAPIView.as_view()),
    path('preparation/create/', recette.api_views.PreparationCreateAPIView.as_view()),
    path('preparation/<int:pk>/update/', recette.api_views.PreparationUpdateAPIView.as_view()),
    path('preparation/<int:pk>/remove/',recette.api_views.PreparationDeleteAPIView.as_view()),

]