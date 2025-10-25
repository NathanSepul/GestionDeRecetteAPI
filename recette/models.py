import base64
from typing import Optional
from django.db import models
from typeRecette.models import TypeRecette
from user.models import User
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _


class Recette(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_("Utilisateur"))
    titre = models.CharField(max_length=100)
    portion = models.IntegerField(blank=False, null=False)
    typeRecette = models.ForeignKey(TypeRecette, models.DO_NOTHING)
    image = models.BinaryField(blank=True, null=True)
    conseil = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'recette'
        unique_together = (('titre', 'typeRecette'),)
        verbose_name = "recette"
        verbose_name_plural = "recettes"
    
    def __str__(self):
        return self.titre

    def image_display(self) -> Optional[str]:
        if self.image:
            return base64.b64encode(self.image).decode('utf-8')
        return None
    
    def image_tag(self) -> Optional[str]:
        if self.image:
            # 1. Convertir les données binaires en Base64
            base64_data = base64.b64encode(self.image).decode('utf-8')
            
            # 2. Créer l'URL de données (data URI)
            # Nous supposons que l'image est un JPEG ou que le type MIME est approprié
            data_uri = f'data:image/jpeg;base64,{base64_data}'
            
            # 3. Utiliser format_html pour générer la balise <img>
            return format_html('<img src="{}" style="max-width: 150px; max-height: 150px;" />', data_uri)
        
        return "Pas d'image"

    image_tag.short_description = 'Aperçu de l\'image'
    
   
    
class Produit(models.Model):
    nom = models.TextField()
    nomPluriel =  models.TextField()
    produitDeBase = models.ForeignKey('self', on_delete=models.DO_NOTHING, verbose_name=_("Produit de base"),blank=True,null=True)
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
    uniteSuperieur = models.ForeignKey('self', on_delete=models.DO_NOTHING, verbose_name=_("Unité superieur"),blank=True,null=True)

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
    unite  = models.ForeignKey(Unite, models.DO_NOTHING, blank=True, null=True)
    produit = models.ForeignKey(Produit, models.DO_NOTHING, blank=True, null=True)

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
    
