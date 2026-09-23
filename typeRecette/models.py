import os
import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.utils.text import slugify
from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver
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


@receiver(post_delete, sender=TypeRecette)
def auto_delete_file_on_delete(sender, instance, **kwargs):
    """Supprime le fichier du disque quand le type de recette est supprimé de la base."""
    if instance.image:
        if os.path.isfile(instance.image.path):
            os.remove(instance.image.path)


@receiver(pre_save, sender=TypeRecette)
def auto_delete_file_on_change(sender, instance, **kwargs):
    """Supprime l'ancien fichier quand une nouvelle image est téléchargée."""
    if not instance.pk:
        return False

    try:
        old_file = TypeRecette.objects.get(pk=instance.pk).image
    except TypeRecette.DoesNotExist:
        return False

    new_file = instance.image
    if old_file and old_file != new_file:
        if os.path.isfile(old_file.path):
            os.remove(old_file.path)