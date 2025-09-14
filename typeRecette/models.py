from django.db import models
from django.utils.translation import gettext_lazy as _
from user.models import User


class TypeRecette(models.Model):
    user = models.ForeignKey(User, on_delete=models.DO_NOTHING, verbose_name=_("Utilisateur"))
    noOrdre = models.IntegerField(db_column='noOrdre', blank=True, null=True) 
    type = models.CharField(max_length=10, blank=False, null=False)

    class Meta:
        db_table = 'type_recette'
        verbose_name = "type de recette"
        verbose_name_plural = "types de recette"
    
    def __str__(self):
        return self.type
