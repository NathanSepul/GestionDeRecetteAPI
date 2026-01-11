import base64
from django.conf import settings
from rest_framework import  serializers

import recette.models
from django.db.models import Max

from tag.models import Tag
from user.serializer import UserSerializer

class RecetteSerializer(serializers.ModelSerializer):
    adapteQuantity = serializers.BooleanField(default=True, write_only=True, required=False  )
    image = serializers.ImageField( required=False, max_length=None, use_url=True)
    
    class Meta:
        model = recette.models.Recette
        fields = ['id', 'titre', 'portion', 'typeRecette','image','conseil', 'adapteQuantity' ]
        
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
        fields = ['id', 'code', 'description']#, 'borneSuperieur', 'uniteSuperieur_id' ] 


# 
# ----------------------------------
# ----------------------------------
# 

class IngredientSerializer(serializers.ModelSerializer):
    produit_detail = ProduitSerializer(source='produit', read_only=True)
    unite_detail = UniteSerializer(source='unite', read_only=True)


    class Meta:
        model = recette.models.Ingredient
        fields = ['id', 'noOrdre', 'isSection', 'quantite', 'nom', 'recette','unite', 'produit','unite_detail', 'produit_detail']
    

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


