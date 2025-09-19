import base64
from django.db import models
from typeRecette.models import TypeRecette
from user.models import User
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

    def image_display(self):
        if self.image:
            return base64.b64encode(self.image).decode('utf-8')
        return None
    


class Ingredient(models.Model):
    recette = models.ForeignKey(Recette,on_delete= models.CASCADE, verbose_name=_("Recette"))
    noOrdre = models.IntegerField()  
    isSection = models.BooleanField(default=False) 
    quantite = models.DecimalField(max_digits=9, decimal_places=2, blank=True, null=True)
    nom = models.TextField()

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
