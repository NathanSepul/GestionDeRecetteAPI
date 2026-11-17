import mimetypes
from django.http import HttpResponse
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework_simplejwt.authentication import JWTAuthentication
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework import permissions
from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import RefreshToken
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
    
# Client web : le refresh token voyage dans un cookie HttpOnly, illisible par le JavaScript de la page (XSS).
# L'app mobile, qui n'envoie pas "refresh_cookie", continue de le recevoir dans le JSON.
REFRESH_COOKIE = 'refresh_token'
REFRESH_COOKIE_PATH = '/api/token/'


def wants_refresh_cookie(request):
    return isinstance(request.data, dict) and request.data.get('refresh_cookie') is True


def move_refresh_to_cookie(response):
    """Retire le refresh token du JSON et le pose en cookie HttpOnly (seulement envoyé à /api/token/...)."""
    refresh = response.data.pop('refresh', None) if response.status_code == 200 else None
    if refresh:
        response.set_cookie(
            REFRESH_COOKIE,
            refresh,
            max_age=int(settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds()),
            path=REFRESH_COOKIE_PATH,
            httponly=True,
            secure=not settings.DEBUG,
            # Strict : jamais envoyé depuis un autre site, ce qui protège aussi /token/refresh/ du CSRF
            samesite='Strict',
        )
    return response


@extend_schema(tags=['Utilisateur'])
class MyLogin(TokenObtainPairView):

    @extend_schema(
        operation_id='Login',
        description='Connexion. Avec "refresh_cookie": true, le refresh token est posé en cookie HttpOnly au lieu du JSON.',
    )
    def post(self, request, *args, **kwargs):
        response = super().post(request, *args, **kwargs)
        return move_refresh_to_cookie(response) if wants_refresh_cookie(request) else response

@extend_schema(tags=['Utilisateur'])
class MyTokenRefreshView(TokenRefreshView):
    @extend_schema(
        operation_id='Refresh token',
        description='Refresh token. Avec "refresh_cookie": true, il est lu dans le cookie HttpOnly au lieu du JSON.',
        # security=[],
    )
    def post(self, request, *args, **kwargs):
        if not wants_refresh_cookie(request):
            return super().post(request, *args, **kwargs)

        serializer = self.get_serializer(data={'refresh': request.COOKIES.get(REFRESH_COOKIE)})
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as e:
            raise InvalidToken(e.args[0])
        return move_refresh_to_cookie(Response(serializer.validated_data, status=status.HTTP_200_OK))

@extend_schema(tags=['Utilisateur'], request=None, responses={204: None})
@api_view(['POST'])
@authentication_classes([])
@permission_classes([AllowAny])
def logout(request):
    """Déconnexion web : invalide le refresh token du cookie et supprime le cookie (le JS ne peut pas le faire)."""
    refresh = request.COOKIES.get(REFRESH_COOKIE)
    if refresh:
        try:
            RefreshToken(refresh).blacklist()
        except TokenError:
            pass  # déjà expiré ou blacklisté
    response = Response(status=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(REFRESH_COOKIE, path=REFRESH_COOKIE_PATH, samesite='Strict')
    return response

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
