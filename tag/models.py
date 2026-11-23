from django.db import models
from recette.models import Recette
from user.models import User
from django.utils.translation import gettext_lazy as _
from django.core.validators import MaxValueValidator

class Tag(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_("Utilisateur"))
    tag = models.CharField(max_length=100)
    recettes= models.ManyToManyField(Recette,related_name='tags') 
    opacite = models.PositiveSmallIntegerField(validators=[MaxValueValidator(255)])
    red = models.PositiveSmallIntegerField(validators=[MaxValueValidator(255)])
    green = models.PositiveSmallIntegerField(validators=[MaxValueValidator(255)])
    blue = models.PositiveSmallIntegerField(validators=[MaxValueValidator(255)])

    class Meta:
        db_table = 'tag'
        verbose_name = "tag"
        verbose_name_plural = "tags"
