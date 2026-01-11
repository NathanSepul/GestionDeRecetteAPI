from django.contrib.auth.models import AbstractBaseUser
from django.contrib.staticfiles.storage import staticfiles_storage
import user.models
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken



class UserBaseSerializer(serializers.ModelSerializer):
    avatar = serializers.ImageField( required=False, max_length=None, use_url=True)
    
    class Meta:
        model = user.models.User
        fields = ['id', 'email', 'first_name', 'last_name', 'avatar']

class UserSerializer(serializers.ModelSerializer):
    date_joined = serializers.DateTimeField(read_only=True)
    email = serializers.ReadOnlyField()
    isFollowed = serializers.SerializerMethodField()
    avatar = serializers.ImageField( required=False, max_length=None, use_url=True)

    class Meta:
        model = user.models.User
        fields = ['id', 'email', 'first_name', 'last_name', 'date_joined', 'language', 'isFollowed', 'avatar']
    
    def get_isFollowed(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            # Vérifie si l'utilisateur connecté suit ce profil
            return request.user.following.filter(id=obj.id).exists()


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
