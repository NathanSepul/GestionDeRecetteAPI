from django.db import models


class TypeRecette(models.Model):
    noOrdre = models.IntegerField(db_column='noOrdre', blank=True, null=True) 
    type = models.CharField(max_length=10, blank=False, null=False)

    class Meta:
        db_table = 'type_recette'
        verbose_name = "type de recette"
        verbose_name_plural = "types de recette"
    
    def __str__(self):
        return self.type
