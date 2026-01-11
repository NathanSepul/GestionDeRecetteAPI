from django.urls import path, include
import recette.api_views

from rest_framework.routers import DefaultRouter
from .api_views import RecetteViewSet,  IngredientViewSet,PreparationViewSet

router = DefaultRouter()

router.register(r'preparation', PreparationViewSet, basename='preparation')
router.register(r'ingredient', IngredientViewSet, basename='ingredient')
router.register(r'', RecetteViewSet, basename='')

urlpatterns = [
    path('produit/',recette.api_views.ProduitListAPIView.as_view()),
    path('unite/',recette.api_views.UniteListAPIView.as_view()),

   path('', include(router.urls)),

]