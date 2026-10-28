import base64
from django.conf import settings
from rest_framework import  serializers

import recette.models
from django.db.models import Max

from tag.models import Tag
from user.serializer import UserSerializer
from gestionDeRecette.serializer import ImageVariantField

class RecetteSerializer(serializers.ModelSerializer):
    adapteQuantity = serializers.BooleanField(default=True, write_only=True, required=False  )
    image = serializers.ImageField( required=False, max_length=None, use_url=True)
    imageThumb = ImageVariantField('image', 'thumb')
    imageMedium = ImageVariantField('image', 'medium')
    
    class Meta:
        model = recette.models.Recette
        fields = ['id', 'titre', 'portion', 'typeRecette','image', 'imageThumb', 'imageMedium', 'conseil', 'source', 'adapteQuantity', 'user_id' ]
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
    