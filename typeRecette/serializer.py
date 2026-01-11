from django.conf import settings
from rest_framework import  serializers
import typeRecette.models


class TypeRecetteSerializer(serializers.ModelSerializer):

    class Meta:
        model = typeRecette.models.TypeRecette
        fields = ['id', 'noOrdre', 'type', ]

class ReorderTypeRecetteSerializer(serializers.Serializer):
    newPosition = serializers.IntegerField(min_value=0)

    class Meta:
        model =  typeRecette.models.TypeRecette
        fields = ['id', 'noOrdre', 'type' ]