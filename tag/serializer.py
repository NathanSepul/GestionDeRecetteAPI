from django.conf import settings
from rest_framework import  serializers
import tag.models


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = tag.models.Tag
        fields = ['id', 'tag', 'red', 'green','blue', 'opcite' ]

class TagRecetteSerializer(serializers.ModelSerializer):
    class Meta:
        model = tag.models.TagRecette
        fields = ['id', 'tag', 'recette']