import os
import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.utils.text import slugify
from gestionDeRecette.utils import register_image_cleanup
from user.models import User


def path_and_rename(instance, filename):
    ext = filename.split('.')[-1]
    clean_name = slugify(instance.type)
    unique_id = uuid.uuid4().hex[:8]
    new_filename = f"{clean_name}_{unique_id}.{ext}"
    return os.path.join('photos/type_recette/', new_filename)

class TypeRecette(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_("Utilisateur"))
    noOrdre = models.IntegerField(db_column='noOrdre', blank=True, null=True) 
    type = models.CharField(max_length=10, blank=False, null=False)
    image = models.ImageField(upload_to=path_and_rename, blank=True, null=True)

    class Meta:
        db_table = 'type_recette'
        verbose_name = "type de recette"
        verbose_name_plural = "types de recette"
    
    def __str__(self):
        return self.type
    
    def image_preview(self):
        if self.image:
            return format_html('<img src="{}" style="width: 100px; height: auto; border-radius: 5px;" />', self.image.url)
        return "Pas d'image"

    image_preview.short_description = 'Aperçu'


register_image_cleanup(TypeRecette, 'image')