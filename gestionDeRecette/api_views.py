import mimetypes
from django.http import HttpResponse, HttpResponseForbidden
from rest_framework.permissions import AllowAny, IsAuthenticated
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

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
@permission_classes([IsAuthenticated])
def serve_image(request, path):
    if not request.user.is_authenticated:
        return HttpResponseForbidden()

    response = HttpResponse()
    response['X-Accel-Redirect'] = f'/internal-media/{path}'
    content_type, encoding = mimetypes.guess_type(path)
    if content_type:
        response['Content-Type'] = content_type
        
    return response