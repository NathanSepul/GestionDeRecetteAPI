import base64
from django.conf import settings
from rest_framework import  serializers

import recette.models
from django.db.models import Max

from tag.models import Tag
from user.serializer import UserSerializer

class RecetteLiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = recette.models.Recette
        fields = ['id', 'titre', 'typeRecette' ]

class RecetteSerializer(serializers.ModelSerializer):
    adapteQuantity = serializers.BooleanField(default=True, write_only=True, required=False  )
    imageNew = serializers.ImageField( required=False, max_length=None, use_url=True)
    
    class Meta:
        model = recette.models.Recette
        fields = ['id', 'titre', 'portion', 'typeRecette','imageNew','conseil', 'adapteQuantity' ]
    
    def create(self, validated_data):
        validated_data.pop('adapteQuantity', None)
        instance = recette.models.Recette.objects.create(user=self.context['request'].user, **validated_data)
        return instance

    def get_imagefield_url(self, obj):
        return obj.get_imagefield_url()


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
    

    def create(self, validated_data):
        recette_instance = validated_data.get('recette')
        if not recette_instance:
            raise serializers.ValidationError({"recette": "Recette ID"})

        max_no_ordre = recette.models.Ingredient.objects.filter( recette=recette_instance ).aggregate(Max('noOrdre'))['noOrdre__max']
        
        next_no_ordre = (max_no_ordre or 0) + 1
        validated_data['noOrdre'] = next_no_ordre

        obj = recette.models.Ingredient.objects.create(**validated_data)
        return obj

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

    def create(self, validated_data):
        recette_instance = validated_data.get('recette')
        if not recette_instance:
            raise serializers.ValidationError({"recette": "Recette ID"})

        max_no_ordre = recette.models.Preparation.objects.filter( recette=recette_instance ).aggregate(Max('noOrdre'))['noOrdre__max']
        
        next_no_ordre = (max_no_ordre or 0) + 1
        validated_data['noOrdre'] = next_no_ordre

        obj = recette.models.Preparation.objects.create(**validated_data)
        return obj


class ReorderPreparationSerializer(serializers.Serializer):
    newPosition = serializers.IntegerField(min_value=0)

    class Meta:
        model = recette.models.Preparation
        fields = ['id', 'noOrdre', 'isSection', 'description', 'recette' ]


