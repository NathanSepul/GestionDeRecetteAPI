from django.db import models
from recette.models import Recette
from user.models import User
from django.utils.translation import gettext_lazy as _

class Tag(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_("Utilisateur"))
    tag = models.CharField(max_length=100)
    recettes= models.ManyToManyField(Recette)
    opacite = models.IntegerField()
    red = models.IntegerField()
    green = models.IntegerField()
    blue = models.IntegerField()


    class Meta:
        db_table = 'tag'
        verbose_name = "tag"
        verbose_name_plural = "tags"

# class TagRecette(models.Model):
#     tag = models.ForeignKey(Tag, models.DO_NOTHING, db_column='idTag') 
#     recette = models.ForeignKey(Recette, models.DO_NOTHING, db_column='idRecette')

#     class Meta:
#         managed = False
#         db_table = 'tagRecette'
#         verbose_name = "tag de la recette"
#         verbose_name_plural = "tags de recette"