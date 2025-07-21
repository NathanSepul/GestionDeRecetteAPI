
# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class TypeRecette(models.Model):
    noOrdre = models.IntegerField(db_column='noOrdre', blank=True, null=True) 
    type = models.CharField(max_length=10, blank=False, null=False)
    pathToSave = models.TextField(db_column='pathToSave', null=True)

    class Meta:
        managed = False
        db_table = 'typeRecette'
        verbose_name = "type de recette"
        verbose_name_plural = "types de recette"
    
    def __str__(self):
        return self.type
