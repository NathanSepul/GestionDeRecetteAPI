from django.conf import settings
from rest_framework import  serializers
import typeRecette.models


class TypeRecetteSerializer(serializers.ModelSerializer):
    recipeCount = serializers.IntegerField(source='recipe_count', read_only=True)

    class Meta:
        model = typeRecette.models.TypeRecette
        fields = ['id', 'noOrdre', 'type', 'recipeCount' ]

class ReorderTypeRecetteSerializer(serializers.Serializer):
    newPosition = serializers.IntegerField(min_value=0)

    class Meta:
        model =  typeRecette.models.TypeRecette
        fields = ['id', 'noOrdre', 'type' ]