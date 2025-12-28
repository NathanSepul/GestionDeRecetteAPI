import os
from django import forms
from django.conf import settings
from django.http import FileResponse, Http404, HttpResponse
from django.contrib.auth.decorators import login_required


# @login_required
def download_apk(request):
    filename = f"{settings.APP_NAME}.apk"
    path_to_file = os.path.join(settings.MEDIA_ROOT, 'uploads/apk',filename)
    if not os.path.exists(path_to_file):
        raise Http404("Le fichier APK est introuvable.")

    # VERSION PRO : On laisse Nginx servir le fichier
    # L'URL interne doit correspondre à la config Nginx ci-dessous
    response = HttpResponse()
    response['Content-Type'] = 'application/vnd.android.package-archive'
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    # Nginx intercepte cet en-tête et sert le fichier lui-même
    # Attention : le chemin doit être relatif à ce que Nginx voit
    response['X-Accel-Redirect'] = f'/internal-media/uploads/apk/{filename}'
    
    return response