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
            nom_fichier = fichier.name.lower()
            extension_attendue = f"{support.lower()}.zip"
            
            if not nom_fichier.endswith(extension_attendue):
                raise ValidationError(
                    f"Erreur d'extension : Pour le support sélectionné, "
                    f"le fichier doit être un '{support}.zip' reçu: '{extension_attendue}'."
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
                os.makedirs(dossier_destination, exist_ok=True)
                
                nom_final = f"{settings.APP_NAME}.{obj.support}.zip"
                chemin_complet = os.path.join(dossier_destination, nom_final)
                
                if os.path.exists(chemin_complet):
                    date_str = datetime.now().strftime('%Y%m%d_%H%M')
                    ancien_nom = f"{settings.APP_NAME}_{date_str}.{obj.support}.zip"
                    os.rename(chemin_complet, os.path.join(dossier_destination, ancien_nom))

                fs = FileSystemStorage(location=dossier_destination)

                fs.save(f"{settings.APP_NAME}.{obj.support}.zip", fichier)

            super().save_model(request, obj, form, change)
        except Exception as e:
            from django.contrib import messages
            messages.error(request, f"Erreur lors de l'upload : {e}")
            