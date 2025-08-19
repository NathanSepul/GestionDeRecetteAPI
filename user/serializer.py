from django.contrib.auth.models import AbstractBaseUser
from django.contrib.staticfiles.storage import staticfiles_storage
import user.models
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken



class UserBaseSerializer(serializers.ModelSerializer):
     class Meta:
        model = user.models.User
        fields = ['id' ]

class UserSerializer(serializers.ModelSerializer):
    date_joined = serializers.DateTimeField(read_only=True)
    email = serializers.ReadOnlyField()

    class Meta:
        model = user.models.User
        fields = ['id', 'email', 'first_name', 'last_name', 'date_joined', 'language']
    

class MyTokenObtainPairSerializer(TokenObtainPairSerializer):

    token_class = RefreshToken

    def validate(self, attrs):
        data = super().validate(attrs)

        refresh = self.get_token(self.user)

        data["refresh"] = str(refresh)
        data["access"] = str(refresh.access_token)
        data["user_id"] = str(self.user.id)

        return data


class LanguageSerializers(serializers.ModelSerializer):

    class Meta:
        model = user.models.User
        fields = ['language']