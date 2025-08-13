# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class Ingredient(models.Model):
    id = models.IntegerField(primary_key=True)
    idrecette = models.ForeignKey('Recette', models.DO_NOTHING, db_column='idRecette')  # Field name made lowercase.
    noordre = models.IntegerField(db_column='noOrdre')  # Field name made lowercase.
    issection = models.IntegerField(db_column='isSection')  # Field name made lowercase.
    quantite = models.DecimalField(max_digits=9, decimal_places=2, blank=True, null=True)
    nom = models.TextField()

    class Meta:
        managed = False
        db_table = 'Ingredient'


class Preparation(models.Model):
    id = models.IntegerField(primary_key=True)
    idrecette = models.ForeignKey('Recette', models.DO_NOTHING, db_column='idRecette')  # Field name made lowercase.
    section = models.CharField(max_length=100, blank=True, null=True)
    noordre = models.IntegerField(db_column='noOrdre')  # Field name made lowercase.
    description = models.TextField()
    issection = models.IntegerField(db_column='isSection')  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'Preparation'


class Recette(models.Model):
    id = models.IntegerField(primary_key=True)
    titre = models.CharField(max_length=100)
    portion = models.IntegerField(blank=True, null=True)
    idtyperecette = models.ForeignKey('Typerecette', models.DO_NOTHING, db_column='idTypeRecette')  # Field name made lowercase.
    image = models.TextField(blank=True, null=True)
    conseil = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'Recette'
        unique_together = (('titre', 'idtyperecette'),)


class Tag(models.Model):
    id = models.IntegerField(primary_key=True)
    tag = models.CharField(max_length=100)
    opacite = models.IntegerField()
    red = models.IntegerField()
    green = models.IntegerField()
    blue = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'Tag'


class Tagrecette(models.Model):
    id = models.IntegerField(primary_key=True)
    idtag = models.ForeignKey(Tag, models.DO_NOTHING, db_column='idTag')  # Field name made lowercase.
    idrecette = models.ForeignKey(Recette, models.DO_NOTHING, db_column='idRecette')  # Field name made lowercase.

    class Meta:
        managed = False
        db_table = 'TagRecette'


class Unite(models.Model):
    id = models.IntegerField(primary_key=True)
    code = models.CharField(max_length=5)
    description = models.CharField(max_length=30)

    class Meta:
        managed = False
        db_table = 'Unite'


class Typerecette(models.Model):
    id = models.IntegerField(primary_key=True)
    noordre = models.IntegerField(db_column='noOrdre', blank=True, null=True)  # Field name made lowercase.
    type = models.CharField(max_length=10, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'typeRecette'
