import base64
from django.conf import settings
from rest_framework import  serializers

import recette.models
from django.db.models import Max

class RecetteSerializer(serializers.ModelSerializer):
    class Meta:
        model = recette.models.Recette
        fields = ['id', 'titre', 'portion', 'typeRecette','image', 'conseil' ]
    
    def get_image(self, obj):
        if obj.image:
            return base64.b64encode(obj.image).decode('utf-8')
        return None
    


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = recette.models.Ingredient
        fields = ['id', 'noOrdre', 'isSection', 'quantite', 'nom', 'recette' ]

    def create(self, validated_data):
        recette_instance = validated_data.get('recette')
        if not recette_instance:
            raise serializers.ValidationError({"recette": "Recette ID"})

        max_no_ordre = recette.models.Ingredient.objects.filter( recette=recette_instance ).aggregate(Max('noOrdre'))['noOrdre__max']

        max_no_ordre =  recette.models.Ingredient.objects.aggregate(Max('noOrdre'))['noOrdre__max']
        
        next_no_ordre = (max_no_ordre or 0) + 1
        validated_data['noOrdre'] = next_no_ordre

        obj = recette.models.Ingredient.objects.create(**validated_data)
        return obj
    


class PreparationSerializer(serializers.ModelSerializer):
    class Meta:
        model = recette.models.Preparation
        fields = ['id', 'noOrdre', 'description', 'isSection', 'description', 'recette' ]

    def create(self, validated_data):
        recette_instance = validated_data.get('recette')
        if not recette_instance:
            raise serializers.ValidationError({"recette": "Recette ID"})

        max_no_ordre = recette.models.Preparation.objects.filter( recette=recette_instance ).aggregate(Max('noOrdre'))['noOrdre__max']

        max_no_ordre =  recette.models.Preparation.objects.aggregate(Max('noOrdre'))['noOrdre__max']
        
        next_no_ordre = (max_no_ordre or 0) + 1
        validated_data['noOrdre'] = next_no_ordre

        obj = recette.models.Preparation.objects.create(**validated_data)
        return obj