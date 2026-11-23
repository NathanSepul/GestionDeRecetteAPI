import os
import appVersion.models
import appVersion.serializer
from django.conf import settings
from django.http import Http404, HttpResponse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions
from rest_framework.views import APIView

class DownloadAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(
    tags=['AppVersion'],
    responses={200: OpenApiTypes.BINARY},
    )
    def get(self, request,support):
        filename = f"{settings.APP_NAME}.{support}.zip"
        path_to_file = os.path.join(settings.MEDIA_ROOT, f'uploads/{support}', filename)

        if not os.path.exists(path_to_file):
            raise Http404(f"Le fichier {support} est introuvable.")

        response = HttpResponse()
        response['Content-Type'] = 'application/zip'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        # Nginx envoie le fichier lui-même (location /internal-media/), Django ne fait que donner le feu vert
        response['X-Accel-Redirect'] = f'/internal-media/uploads/{support}/{filename}'
        
        return response

@extend_schema(tags=['AppVersion'])
class AppVersionSupportAPIView(generics.RetrieveAPIView):
    queryset = appVersion.models.AppVersion.objects.all()
    serializer_class = appVersion.serializer.VersionSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'support'