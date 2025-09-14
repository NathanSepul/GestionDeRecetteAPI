from django.conf import settings
from rest_framework import  serializers
from django.db.models import Max
import typeRecette.models


class TypeRecetteSerializer(serializers.ModelSerializer):

    class Meta:
        model = typeRecette.models.TypeRecette
        fields = ['id', 'noOrdre', 'type', ]

    def create(self, validated_data):
        max_no_ordre =  typeRecette.models.TypeRecette.objects.aggregate(Max('noOrdre'))['noOrdre__max']
        next_no_ordre = (max_no_ordre or 0) + 1
        validated_data['noOrdre'] = next_no_ordre
        instance = typeRecette.models.TypeRecette.objects.create(user=self.context['request'].user, **validated_data)
        return instance

class ReorderTypeRecetteSerializer(serializers.Serializer):
    newPosition = serializers.IntegerField(min_value=0)

    class Meta:
        model =  typeRecette.models.TypeRecette
        fields = ['id', 'noOrdre', 'type' ]