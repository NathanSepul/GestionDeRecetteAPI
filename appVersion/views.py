import os
from django import forms
from django.conf import settings
from django.http import FileResponse, Http404, HttpResponseRedirect
from django.shortcuts import render

def download_apk(request):
    # Chemin vers votre fichier APK
    path_to_file = os.path.join(settings.MEDIA_ROOT, 'uploads/apk',f"{settings.APP_NAME}.apk")
    print(path_to_file)
    
    if os.path.exists(path_to_file):
        # 'as_attachment=True' force le téléchargement sur le GSM
        response = FileResponse(open(path_to_file, 'rb'), content_type='application/vnd.android.package-archive')
        response['Content-Disposition'] = 'attachment; filename="Mes recette.apk"'
        return response
    
    raise Http404("Le fichier APK est introuvable.")