import mimetypes
from django.http import HttpResponse
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework import permissions
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

class IsOwner(permissions.BasePermission):
    """
    Permission permettant de ne laisser que le propriétaire modifier l'objet.
    """
    def has_object_permission(self, request, view, obj):
        
        print(request.user)
        if hasattr(obj, 'user'):
            print(f'direct {obj.user}')
            return obj.user == request.user
        
        if hasattr(obj, 'recette'):
            print('indirect {obj.user}' )
            return obj.recette.user == request.user
            
        return False
    
@extend_schema(tags=['Utilisateur'])
class MyLogin(TokenObtainPairView):

    @extend_schema(
        operation_id='Login',
        description='Connexion',
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

@extend_schema(tags=['Utilisateur'])
class MyTokenRefreshView(TokenRefreshView):
    @extend_schema(
        operation_id='Refresh token',
        description='Refresh token',
        # security=[],
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

@extend_schema(tags=['Utilisateur'])
class MyTokenVerifyView(TokenVerifyView):
    @extend_schema(
        operation_id='Verify token',
        description='Verify token',
        # security=[],
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

@api_view(['GET'])
@authentication_classes([SessionAuthentication, TokenAuthentication, JWTAuthentication])
@permission_classes([IsAuthenticated])
def serve_image(request, path):
    response = HttpResponse()
    response['X-Accel-Redirect'] = f'/internal-media/{path}'
    content_type, encoding = mimetypes.guess_type(path)
    response['Content-Type'] = content_type or 'image/png' 

    return response
