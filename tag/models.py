from django.db import models
from recette.models import Recette

class Tag(models.Model):
    tag = models.CharField(max_length=100)
    opcite = models.IntegerField()
    red = models.IntegerField()
    green = models.IntegerField()
    blue = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'Tag'
        verbose_name = "tag"
        verbose_name_plural = "tags"

class TagRecette(models.Model):
    tag = models.ForeignKey(Tag, models.DO_NOTHING, db_column='idTag') 
    recette = models.ForeignKey(Recette, models.DO_NOTHING, db_column='idRecette')

    class Meta:
        managed = False
        db_table = 'TagRecette'
        verbose_name = "tag de la recette"
        verbose_name_plural = "tags de recette"