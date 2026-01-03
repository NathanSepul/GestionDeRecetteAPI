import os
import appVersion.models
import appVersion.serializer
from django import forms
from django.conf import settings
from django.http import FileResponse, Http404, HttpResponse
from django.contrib.auth.decorators import login_required
from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView 


class DownloadAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    @extend_schema(tags=['AppVersion'])
    def get(self, request,support):
        filename = f"{settings.APP_NAME}.{support}"
        path_to_file = os.path.join(settings.MEDIA_ROOT, f'uploads/{support}', filename)

        # 2. Vérification de l'existence
        if not os.path.exists(path_to_file):
            raise Http404(f"Le fichier {support} est introuvable.")

        # 3. Préparation de la réponse
        response = HttpResponse()
        response['Content-Type'] = 'application/vnd.android.package-archive'
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        # 4. Optimisation Nginx (X-Accel-Redirect)
        # Note : On utilise généralement le paramètre 'support' pour router vers le bon fichier si nécessaire
        response['X-Accel-Redirect'] = f'/internal-media/uploads/{support}/{filename}'
        
        return response

@extend_schema(tags=['AppVersion'])
class AppVersionSupportAPIView(generics.RetrieveAPIView):
    queryset = appVersion.models.AppVersion.objects.all()
    serializer_class = appVersion.serializer.VersionSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'support'