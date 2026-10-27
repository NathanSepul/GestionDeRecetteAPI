from rest_framework import serializers
import listeCourse.models
from recette.models import Rayon
from recette.serializer import ProduitSerializer, RayonSerializer, UniteSerializer


class ArticleSerializer(serializers.ModelSerializer):
    produit = ProduitSerializer(read_only=True)
    unite = UniteSerializer(read_only=True)
    rayon = RayonSerializer(read_only=True)

    class Meta:
        model = listeCourse.models.ListeCourseArticle
        fields = ['id', 'produit', 'nom', 'precision', 'unite', 'quantite', 'rayon', 'placard', 'coche', 'manuel']
        read_only_fields = fields


class ArticleManuelSerializer(serializers.Serializer):
    nom = serializers.CharField(max_length=200)
    rayon = serializers.PrimaryKeyRelatedField(queryset=Rayon.objects.all(), required=False, allow_null=True)


class ArticleCocheSerializer(serializers.Serializer):
    coche = serializers.BooleanField()


class ListeCourseRecetteSerializer(serializers.ModelSerializer):
    recetteId = serializers.IntegerField(source='recette_id', read_only=True)
    titre = serializers.CharField(source='recette.titre', read_only=True)
    portionRecette = serializers.IntegerField(source='recette.portion', read_only=True)

    class Meta:
        model = listeCourse.models.ListeCourseRecette
        fields = ['recetteId', 'titre', 'portion', 'portionRecette']


class AjoutRecetteSerializer(serializers.Serializer):
    recetteId = serializers.IntegerField()
    portion = serializers.IntegerField(min_value=1)


class ListeCourseResumeSerializer(serializers.ModelSerializer):
    nbRecettes = serializers.IntegerField(read_only=True)
    nbArticles = serializers.IntegerField(read_only=True)
    nbCoches = serializers.IntegerField(read_only=True)

    class Meta:
        model = listeCourse.models.ListeCourse
        fields = ['id', 'nom', 'dateModification', 'nbRecettes', 'nbArticles', 'nbCoches']
        read_only_fields = ['id', 'dateModification']


class ListeCourseSerializer(serializers.ModelSerializer):
    recettes = ListeCourseRecetteSerializer(many=True, read_only=True)
    articles = serializers.SerializerMethodField()

    class Meta:
        model = listeCourse.models.ListeCourse
        fields = ['id', 'nom', 'dateCreation', 'dateModification', 'recettes', 'articles']
        read_only_fields = ['id', 'dateCreation', 'dateModification']

    def get_articles(self, liste):
        # même ordre que la liste de courses d'une recette : rayon, sans rayon, placard en dernier
        articles = sorted(liste.articles.all(), key=lambda a: (
            a.placard,
            a.rayon.noOrdre if a.rayon else float('inf'),
            (a.produit.nom if a.produit else (a.nom or '')).lower(),
        ))
        return ArticleSerializer(articles, many=True).data
