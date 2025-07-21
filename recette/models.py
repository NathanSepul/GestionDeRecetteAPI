from django.db import models
from typeRecette.models import TypeRecette

class Recette(models.Model):
    titre = models.CharField(max_length=100)
    portion = models.IntegerField(blank=False, null=False)
    typeRecette = models.ForeignKey(TypeRecette, models.DO_NOTHING, db_column='idTypeRecette')
    image = models.BinaryField(blank=True, null=True)
    conseil = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'Recette'
        unique_together = (('titre', 'typeRecette'),)
        verbose_name = "recette"
        verbose_name_plural = "recettes"
    
    def __str__(self):
        return self.titre
    
    def getImage(self):
        self.image 
    


class Ingredient(models.Model):
    recette = models.ForeignKey(Recette, models.DO_NOTHING, db_column='idRecette', related_name="ingredients")  
    noOrdre = models.IntegerField()  
    isSection = models.BooleanField(default=False) 
    quantite = models.DecimalField(max_digits=9, decimal_places=2, blank=True, null=True)
    nom = models.TextField()

    class Meta:
        managed = False
        db_table = 'Ingredient'
        verbose_name = "ingredient"
        verbose_name_plural = "ingredients"
    
    

class Preparation(models.Model):
    recette = models.ForeignKey(Recette, models.DO_NOTHING, db_column='idRecette')
    noOrdre = models.IntegerField()
    description = models.TextField()
    isSection = models.BooleanField(default=False)

    class Meta:
        managed = False
        db_table = 'Preparation'
        verbose_name = "preparation"
        verbose_name_plural = "preparations"
    
    def __str__(self):
        if (len(self.description) > 30):
            return "%s..." % self.description[:30]
        return self.description
