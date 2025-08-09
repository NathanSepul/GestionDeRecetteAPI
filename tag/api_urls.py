from django.urls import path

import tag.api_views


urlpatterns = [
    path('',tag.api_views.TagListAPIView.as_view()),
    path('create/',tag.api_views.TagCreateAPIView.as_view()),
    path('<int:pk>/update/',tag.api_views.TagUpdateAPIView.as_view()),
    path('<int:pk>/remove/',tag.api_views.TagDeleteAPIView.as_view()),

    path('recette/link/',tag.api_views.TagRecetteCreateAPIView.as_view()),
    # path('recette/link/<int:pk>/update/',tag.api_views.TagRecetteUpdateAPIView.as_view()),
    path('recette/link/<int:pk>/remove/',tag.api_views.TagRecetteDeleteAPIView.as_view()),

]