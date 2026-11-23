import os
from datetime import datetime
from django import forms
from django.conf import settings
from django.contrib import admin
from django.core.exceptions import ValidationError
import appVersion.models


def chemin_application(support):
    """media/uploads/<support>/<APP_NAME>.<support>.zip : le fichier servi par l'endpoint de téléchargement."""
    return os.path.join(settings.MEDIA_ROOT, 'uploads', support, f"{settings.APP_NAME}.{support}.zip")


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
            extension_attendue = f"{support.lower()}.zip"
            if not fichier.name.lower().endswith(extension_attendue):
                raise ValidationError(
                    f"Pour le support sélectionné, le fichier doit se terminer par '{extension_attendue}' "
                    f"(reçu : '{fichier.name}')."
                )

        return cleaned_data


@admin.register(appVersion.models.AppVersion)
class AppVersionAdmin(admin.ModelAdmin):
    form = AppVersionAdminForm

    def save_model(self, request, obj, form, change):
        # Pas de try/except : en cas d'échec, l'admin affiche l'erreur au lieu de « enregistré avec succès »
        # et la version en base n'est pas modifiée.
        fichier = form.cleaned_data.get('app_file')
        if fichier:
            chemin = chemin_application(obj.support)
            os.makedirs(os.path.dirname(chemin), exist_ok=True)

            # Écrit d'abord dans un fichier temporaire : si l'écriture échoue, l'ancienne version reste en place
            temporaire = f"{chemin}.upload"
            with open(temporaire, 'wb') as destination:
                for morceau in fichier.chunks():
                    destination.write(morceau)

            if os.path.exists(chemin):
                date_str = datetime.now().strftime('%Y%m%d_%H%M%S')
                archive = os.path.join(os.path.dirname(chemin), f"{settings.APP_NAME}_{date_str}.{obj.support}.zip")
                os.rename(chemin, archive)
            os.replace(temporaire, chemin)

        super().save_model(request, obj, form, change)
