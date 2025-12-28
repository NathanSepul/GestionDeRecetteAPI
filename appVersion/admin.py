from datetime import datetime
import os
from django.core.exceptions import ValidationError
from django.contrib import admin
from django import forms
from django.core.files.storage import FileSystemStorage
from gestionDeRecette import settings
from django.conf import settings
from rest_framework import status
import appVersion.models

class AppVersionAdminForm(forms.ModelForm):
    app_file = forms.FileField(
        required=True, 
        label="Application",
        help_text="Le fichier doit correspondre au support sélectionné."
    )

    class Meta:
        model = appVersion.models.AppVersion
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        support = cleaned_data.get('support')
        fichier = cleaned_data.get('app_file')

        if support and fichier:
            extension = os.path.splitext(fichier.name)[1].lower().replace('.', '')
            
            if extension != support:
                raise ValidationError(
                    f"Erreur d'extension : Pour le support sélectionné, "
                    f"le fichier doit être un '.{support}' (reçu: '.{extension}')."
                )
        
        return cleaned_data

@admin.register(appVersion.models.AppVersion)
class AppVersionAdmin(admin.ModelAdmin):
    form = AppVersionAdminForm

    def save_model(self, request, obj, form, change):
        try:
            fichier = form.cleaned_data.get('app_file')
            
            if fichier:
                dossier_destination = os.path.join(settings.MEDIA_ROOT, 'uploads', obj.support)

                if not os.path.exists(dossier_destination):
                    print("creation dossier")
                    os.makedirs(dossier_destination, exist_ok=True)
                
                chemin_complet = os.path.join(dossier_destination, f"{settings.APP_NAME}.{obj.support}")
                
                if os.path.exists(chemin_complet):
                    print("rename old")
                    date_str = datetime.now().strftime('%Y%m%d_%H%M')
                    nouveau_chemin_ancien = os.path.join(dossier_destination, f"{settings.APP_NAME}_{date_str}.{obj.support}")
                    os.rename(chemin_complet, nouveau_chemin_ancien)

                fs = FileSystemStorage(location=dossier_destination)
                fs.save(f"{settings.APP_NAME}.{obj.support}", fichier)

            super().save_model(request, obj, form, change)
        except Exception as e:
            print(f"!!! ERREUR UPLOAD : {str(e)}")
            