import base64
import os
from typing import Optional
import uuid
from django.db import models
from typeRecette.models import TypeRecette
from user.models import User
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.utils.text import slugify
from django.contrib.staticfiles.storage import staticfiles_storage
from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver

def path_and_rename(instance, filename):
        ext = filename.split('.')[-1]
        clean_name = slugify(instance.titre)
        unique_id = uuid.uuid4().hex[:8]
        new_filename = f"{clean_name}_{unique_id}.{ext}"
        return os.path.join('photos/', new_filename)

class Recette(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_("Utilisateur"))
    titre = models.CharField(max_length=100)
    portion = models.IntegerField(blank=False, null=False)
    typeRecette = models.ForeignKey(TypeRecette, on_delete=models.PROTECT, verbose_name=_("Type de recette"))
    imageOld = models.BinaryField(blank=True, null=True)
    image = models.ImageField(upload_to=path_and_rename, blank=True, null=True,)
    conseil = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'recette'
        unique_together = (('titre', 'typeRecette'),)
        verbose_name = "recette"
        verbose_name_plural = "recettes"
    
    def __str__(self):
        return self.titre
    
    def image_preview(self):
        if self.image:
            return format_html('<img src="{}" style="width: 100px; height: auto; border-radius: 5px;" />', self.image.url)
        return "Pas d'image"
    
    image_preview.short_description = 'Aperçu'


@receiver(post_delete, sender=Recette)
def auto_delete_file_on_delete(sender, instance, **kwargs):
    """Supprime le fichier du disque quand la recette est supprimée de la base."""
    if instance.image:
        if os.path.isfile(instance.image.path):
            os.remove(instance.image.path)

@receiver(pre_save, sender=Recette)
def auto_delete_file_on_change(sender, instance, **kwargs):
    """Supprime l'ancien fichier quand une nouvelle image est téléchargée."""
    if not instance.pk:
        return False

    try:
        old_file = Recette.objects.get(pk=instance.pk).image
    except Recette.DoesNotExist:
        return False

    new_file = instance.image
    if old_file and old_file != new_file:
        if os.path.isfile(old_file.path):
            os.remove(old_file.path)
   
    
class Produit(models.Model):
    nom = models.TextField(unique=True)
    nomPluriel =  models.TextField()
    produitDeBase = models.ForeignKey('self', on_delete=models.PROTECT, verbose_name=_("Produit de base"),blank=True,null=True)
    determinant =  models.TextField(max_length=5,blank=True,null=True)

    class Meta:
        db_table = 'produit'
        verbose_name = "produit"
        verbose_name_plural = "produits"
    
    def __str__(self):
        return self.nom

class Unite(models.Model):
    code = models.TextField(max_length=5)
    description = models.TextField()
    borneSuperieur = models.IntegerField(blank=True,null=True)
    uniteSuperieur = models.ForeignKey('self', on_delete=models.PROTECT, verbose_name=_("Unité superieur"),blank=True,null=True)

    class Meta:
        db_table = 'unite'
        verbose_name = "unité"
        verbose_name_plural = "unités"
    
    def __str__(self):
        if (len(self.description) > 30):
            return "%s..." % self.description[:30]
        return self.description

class Ingredient(models.Model):
    recette = models.ForeignKey(Recette,on_delete= models.CASCADE, verbose_name=_("Recette"))
    noOrdre = models.IntegerField()  
    isSection = models.BooleanField(default=False) 
    quantite = models.DecimalField(max_digits=9, decimal_places=2, blank=True, null=True)
    nom = models.TextField(blank=True,null=True)
    unite  = models.ForeignKey(Unite, on_delete=models.PROTECT, blank=True, null=True)
    produit = models.ForeignKey(Produit, on_delete=models.PROTECT, blank=True, null=True)

    class Meta:
        db_table = 'ingredient'
        verbose_name = "ingredient"
        verbose_name_plural = "ingredients"
    
    
    

class Preparation(models.Model):
    recette = models.ForeignKey(Recette, on_delete=models.CASCADE, verbose_name=_("Recette"))
    noOrdre = models.IntegerField()
    description = models.TextField()
    isSection = models.BooleanField(default=False)

    class Meta:
        db_table = 'preparation'
        verbose_name = "preparation"
        verbose_name_plural = "preparations"
    
    def __str__(self):
        if (len(self.description) > 30):
            return "%s..." % self.description[:30]
        return self.description
    
