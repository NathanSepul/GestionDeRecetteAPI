from rest_framework import serializers

import recette.models
from gestionDeRecette.serializer import ImageVariantField

class RecetteSerializer(serializers.ModelSerializer):
    adapteQuantity = serializers.BooleanField(default=True, write_only=True, required=False  )
    image = serializers.ImageField( required=False, max_length=None, use_url=True)
    imageThumb = ImageVariantField('image', 'thumb')
    imageMedium = ImageVariantField('image', 'medium')
    # préparation + cuisson + repos, en minutes (null si aucune durée n'est renseignée)
    tempsTotal = serializers.IntegerField(source='temps_total', read_only=True)

    class Meta:
        model = recette.models.Recette
        fields = ['id', 'titre', 'portion', 'typeRecette','image', 'imageThumb', 'imageMedium', 'conseil', 'source',
                  'tempsPreparation', 'tempsCuisson', 'tempsRepos', 'tempsTotal', 'cout', 'difficulte',
                  'adapteQuantity', 'user_id' ]
        read_only_fields = ['source']

    def validate_typeRecette(self, value):
        """Le type de recette doit appartenir à l'utilisateur connecté (création comme modification)."""
        request = self.context.get('request')
        if request and value.user_id != request.user.id:
            raise serializers.ValidationError("Ce type de recette ne vous appartient pas.")
        return value

class ImportRecetteSerializer(serializers.Serializer):
    recetteId = serializers.IntegerField()
    typeRecette = serializers.IntegerField()

class ImportUrlSerializer(serializers.Serializer):
    url = serializers.URLField(max_length=500)
    typeRecette = serializers.IntegerField()
    importerImage = serializers.BooleanField(default=True)

class ImportVideoSerializer(serializers.ModelSerializer):
    """Suivi d'un import vidéo ; recette = id de la recette créée une fois terminé."""
    class Meta:
        model = recette.models.ImportVideo
        fields = ['id', 'statut', 'recette', 'erreur']

class ImportSiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = recette.models.SiteImport
        fields = ['nom', 'domaine', 'url']
# 
# ----------------------------------
# ----------------------------------
#

class ProduitSerializer(serializers.ModelSerializer):
    class Meta:
        model = recette.models.Produit
        fields = ['id', 'nom', 'nomPluriel', 'determinant' ]

class UniteSerializer(serializers.ModelSerializer):
    class Meta:
        model = recette.models.Unite
        fields = ['id', 'code', 'pluriel', 'description']#, 'borneSuperieur', 'uniteSuperieur_id' ]


# 
# ----------------------------------
# ----------------------------------
# 

class IngredientSerializer(serializers.ModelSerializer):
    produit_detail = ProduitSerializer(source='produit', read_only=True)
    unite_detail = UniteSerializer(source='unite', read_only=True)


    class Meta:
        model = recette.models.Ingredient
        fields = ['id', 'noOrdre', 'isSection', 'quantite', 'nom', 'recette','unite', 'produit', 'preparation', 'unite_detail', 'produit_detail']


class ReorderIngredientSerializer(serializers.Serializer):
    newPosition = serializers.IntegerField(min_value=0)

    class Meta:
        model = recette.models.Ingredient
        fields = ['id', 'noOrdre', 'isSection', 'quantite', 'nom', 'recette', 'produit', 'unite' ]

# 
# ----------------------------------
# ----------------------------------
#

class PreparationSerializer(serializers.ModelSerializer):
    class Meta:
        model = recette.models.Preparation
        fields = ['id', 'noOrdre', 'isSection', 'description', 'recette' ]

class ReorderPreparationSerializer(serializers.Serializer):
    newPosition = serializers.IntegerField(min_value=0)

    class Meta:
        model = recette.models.Preparation
        fields = ['id', 'noOrdre', 'isSection', 'description', 'recette' ]


# 
# ----------------------------------
# ----------------------------------
#
 
class ListeCourseRequestSerializer(serializers.Serializer):
    recetteId = serializers.IntegerField()
    portion = serializers.IntegerField(min_value=1)


class RayonSerializer(serializers.ModelSerializer):
    class Meta:
        model = recette.models.Rayon
        fields = ['id', 'nom', 'noOrdre']


class ListeCourseItemSerializer(serializers.Serializer):
    rayon = RayonSerializer(allow_null=True)
    placard = serializers.BooleanField()
    produit = ProduitSerializer(allow_null=True)
    nom = serializers.CharField(allow_null=True)  # ingrédient sans produit lié : le front affiche ce nom
    precision = serializers.CharField(allow_null=True)  # produits regroupés sous ce produit de base ("jus de citron")
    unite = UniteSerializer(allow_null=True)
    quantite = serializers.DecimalField(max_digits=9, decimal_places=2, allow_null=True)
    

#
# ----------------------------------
# Enregistrement complet d'une recette (une seule transaction)
# ----------------------------------
#

class LigneIngredientSerializer(serializers.ModelSerializer):
    """Ligne de la liste finale : avec id = ingrédient existant à modifier, sans id = à créer. L'ordre de la liste donne noOrdre."""
    id = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = recette.models.Ingredient
        fields = ['id', 'isSection', 'quantite', 'nom', 'unite', 'produit', 'preparation']


class LigneEtapeSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(required=False, allow_null=True)

    class Meta:
        model = recette.models.Preparation
        fields = ['id', 'isSection', 'description']


class EnregistrementRecetteSerializer(serializers.Serializer):
    """
    État complet de la recette après édition. Les listes remplacent celles en base :
    une ligne en base absente de la liste est supprimée.
    """
    recette = serializers.DictField()
    ingredients = LigneIngredientSerializer(many=True)
    etapes = LigneEtapeSerializer(many=True)
    # null = tags non modifiés
    tags = serializers.ListField(child=serializers.IntegerField(), allow_null=True, required=False, default=None)
    adapteQuantity = serializers.BooleanField(default=False)

    @staticmethod
    def _ids_uniques(lignes):
        ids = [ligne['id'] for ligne in lignes if ligne.get('id')]
        if len(ids) != len(set(ids)):
            raise serializers.ValidationError("Une même ligne apparaît deux fois.")
        return lignes

    def validate_ingredients(self, lignes):
        return self._ids_uniques(lignes)

    def validate_etapes(self, lignes):
        return self._ids_uniques(lignes)
