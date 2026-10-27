from django.db import models
from django.utils.translation import gettext_lazy as _
from recette.models import Produit, Rayon, Recette, Unite
from user.models import User


class ListeCourse(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_("Utilisateur"))
    nom = models.CharField(max_length=100)
    dateCreation = models.DateTimeField(auto_now_add=True)
    dateModification = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'liste_course'
        verbose_name = "liste de courses"
        verbose_name_plural = "listes de courses"
        ordering = ['-dateModification']

    def __str__(self):
        return self.nom


class ListeCourseRecette(models.Model):
    """Recette ajoutée à la liste, avec le nombre de portions voulu."""
    liste = models.ForeignKey(ListeCourse, on_delete=models.CASCADE, related_name='recettes')
    recette = models.ForeignKey(Recette, on_delete=models.CASCADE)
    portion = models.PositiveIntegerField()

    class Meta:
        db_table = 'liste_course_recette'
        constraints = [models.UniqueConstraint(fields=['liste', 'recette'], name='UniciteRecetteParListeCourse')]


class ListeCourseArticle(models.Model):
    """
    Ligne de la liste. Les articles générés (manuel=False) sont recalculés quand les recettes changent ;
    les articles ajoutés à la main (manuel=True) ne sont jamais touchés par ce recalcul.
    """
    liste = models.ForeignKey(ListeCourse, on_delete=models.CASCADE, related_name='articles')
    produit = models.ForeignKey(Produit, on_delete=models.SET_NULL, blank=True, null=True)
    nom = models.TextField(blank=True, null=True)  # article libre ("papier toilette") ou ingrédient sans produit
    precision = models.TextField(blank=True, null=True)  # "jus de citron" regroupé sous "citron"
    unite = models.ForeignKey(Unite, on_delete=models.SET_NULL, blank=True, null=True)
    quantite = models.DecimalField(max_digits=9, decimal_places=2, blank=True, null=True)
    rayon = models.ForeignKey(Rayon, on_delete=models.SET_NULL, blank=True, null=True)
    placard = models.BooleanField(default=False)
    coche = models.BooleanField(default=False)
    manuel = models.BooleanField(default=False)

    class Meta:
        db_table = 'liste_course_article'
        verbose_name = "article"
        verbose_name_plural = "articles"

    def __str__(self):
        return self.produit.nom if self.produit_id else (self.nom or '')
