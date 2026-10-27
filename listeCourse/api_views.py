from django.db.models import Count, Prefetch, Q
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from listeCourse.models import ListeCourse, ListeCourseArticle, ListeCourseRecette
from listeCourse.serializer import (
    AjoutRecetteSerializer, ArticleCocheSerializer, ArticleManuelSerializer, ArticleSerializer,
    ListeCourseResumeSerializer, ListeCourseSerializer,
)
from listeCourse.services import regenerer_articles
from recette.models import Recette


@extend_schema(tags=['Liste de courses'])
class ListeCourseViewSet(viewsets.ModelViewSet):
    """Listes de courses de l'utilisateur connecté : recettes, articles générés ou ajoutés à la main, cases cochées."""
    serializer_class = ListeCourseSerializer
    pagination_class = None
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        # chaque utilisateur ne voit que ses propres listes
        queryset = ListeCourse.objects.filter(user=self.request.user)
        if self.action == 'list':
            return queryset.annotate(
                nbRecettes=Count('recettes', distinct=True),
                nbArticles=Count('articles', distinct=True),
                nbCoches=Count('articles', filter=Q(articles__coche=True), distinct=True),
            )
        return queryset.prefetch_related(
            Prefetch('recettes', queryset=ListeCourseRecette.objects.select_related('recette')),
            Prefetch('articles', queryset=ListeCourseArticle.objects.select_related('produit', 'unite', 'rayon')),
        )

    def get_serializer_class(self):
        if self.action == 'list':
            return ListeCourseResumeSerializer
        # serializer_class vaut celui déclaré sur l'@action (AjoutRecetteSerializer...) pendant une action
        return super().get_serializer_class()

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def _reponse(self, liste, code=status.HTTP_200_OK):
        return Response(ListeCourseSerializer(self.get_queryset().get(pk=liste.pk)).data, status=code)

    @action(detail=True, methods=['post'], serializer_class=AjoutRecetteSerializer)
    def recettes(self, request, pk=None):
        """Ajoute une recette à la liste (ou change son nombre de portions), puis recalcule les articles."""
        liste = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        recette = get_object_or_404(Recette, pk=serializer.validated_data['recetteId'])

        ListeCourseRecette.objects.update_or_create(
            liste=liste, recette=recette, defaults={'portion': serializer.validated_data['portion']},
        )
        regenerer_articles(liste)
        return self._reponse(liste)

    @action(detail=True, methods=['delete'], url_path=r'recettes/(?P<recette_id>\d+)')
    def retirer_recette(self, request, pk=None, recette_id=None):
        liste = self.get_object()
        liste.recettes.filter(recette_id=recette_id).delete()
        regenerer_articles(liste)
        return self._reponse(liste)

    @action(detail=True, methods=['post'])
    def actualiser(self, request, pk=None):
        """Recalcule les articles (utile si une recette de la liste a été modifiée entre-temps)."""
        liste = self.get_object()
        regenerer_articles(liste)
        return self._reponse(liste)

    @action(detail=True, methods=['post'], serializer_class=ArticleManuelSerializer)
    def articles(self, request, pk=None):
        """Ajoute un article à la main ("papier toilette")."""
        liste = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        article = ListeCourseArticle.objects.create(
            liste=liste, nom=serializer.validated_data['nom'], rayon=serializer.validated_data.get('rayon'), manuel=True,
        )
        liste.save(update_fields=['dateModification'])
        return Response(ArticleSerializer(article).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['patch', 'delete'], url_path=r'articles/(?P<article_id>\d+)', serializer_class=ArticleCocheSerializer)
    def article(self, request, pk=None, article_id=None):
        """PATCH : coche / décoche l'article. DELETE : le retire (un article généré reviendra au prochain recalcul)."""
        liste = self.get_object()
        article = get_object_or_404(ListeCourseArticle, pk=article_id, liste=liste)

        if request.method == 'DELETE':
            article.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        article.coche = serializer.validated_data['coche']
        article.save(update_fields=['coche'])
        liste.save(update_fields=['dateModification'])
        return Response(ArticleSerializer(article).data)

    @action(detail=True, methods=['post'])
    def decocher(self, request, pk=None):
        """Décoche tous les articles (réutiliser la liste pour les courses suivantes)."""
        liste = self.get_object()
        liste.articles.update(coche=False)
        return self._reponse(liste)
