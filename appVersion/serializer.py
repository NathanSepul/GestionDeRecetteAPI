from rest_framework import  serializers

import appVersion.models

class VersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = appVersion.models.AppVersion
        fields = ['version_number']
