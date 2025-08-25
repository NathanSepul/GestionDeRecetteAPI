from django.conf import settings
from rest_framework import  serializers
import recette
import tag.models


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = tag.models.Tag
        fields = ['id', 'tag', 'red', 'green','blue', 'opacite' ]

class TagsRecetteSerializer(serializers.Serializer):
    idRecette = serializers.IntegerField(write_only=True)

    class Meta:
        model = tag.models.Tag
        fields = ['id', 'tag', 'red', 'green','blue', 'opacite' ]

class TagRecetteLinkSerializer(serializers.Serializer):
    recette_id = serializers.IntegerField()
    tag_id = serializers.IntegerField()