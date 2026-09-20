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
    - Lecture (GET, HEAD, OPTIONS) : autorisée à tout utilisateur authentifié.
    - Écriture (PUT, PATCH, DELETE) : autorisée uniquement au propriétaire.
    """

    def has_object_permission(self, request, view, obj):
        # 1. Lecture autorisée pour tout le monde (SAFE_METHODS)
        if request.method in permissions.SAFE_METHODS:
            return True

        # 2. Si l'objet est directement l'utilisateur (ex: UserViewSet)
        if obj == request.user:
            return True

        # 3. Si l'objet est lié à un utilisateur (ex: Recette, Commentaire...)
        if hasattr(obj, 'user_id'):
            return obj.user_id == request.user.id
            
        if hasattr(obj, 'user'):
            return obj.user == request.user

        # 4. Si l'objet est lié à une recette (ex: IngrédientRecette...)
        if hasattr(obj, 'recette') and hasattr(obj.recette, 'user_id'):
            return obj.recette.user_id == request.user.id

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
