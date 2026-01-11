from django.conf import settings
from rest_framework import  serializers
import tag.models


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = tag.models.Tag
        fields = ['id', 'tag', 'red', 'green','blue', 'opacite' ]


class TagRecetteLinkSerializer(serializers.Serializer):
    recette_id = serializers.IntegerField()
    tag_id = serializers.IntegerField()