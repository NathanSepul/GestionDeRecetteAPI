import os
import re
import uuid
from django.db import models
from typeRecette.models import TypeRecette
from user.models import User
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.utils.text import slugify
from django.db.models import Q
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from gestionDeRecette.utils import register_image_cleanup

def path_and_rename(instance, filename):
        ext = filename.split('.')[-1]
        clean_name = slugify(instance.titre)
        unique_id = uuid.uuid4().hex[:8]
        new_filename = f"{clean_name}_{unique_id}.{ext}"
        return os.path.join('photos/', new_filename)


# Durées en minutes ; au-delà d'une semaine c'est forcément une faute de frappe
DUREE_MAX_MINUTES = 7 * 24 * 60


def formater_duree(minutes):
    """90 -> '1 h 30 min', 45 -> '45 min', 120 -> '2 h'."""
    heures, reste = divmod(minutes, 60)
    if not heures:
        return f"{reste} min"
    return f"{heures} h {reste} min" if reste else f"{heures} h"


class Recette(models.Model):
    class Cout(models.IntegerChoices):
        FAIBLE = 1, _("Faible")
        MOYEN = 2, _("Moyen")
        ELEVE = 3, _("Élevé")

    class Difficulte(models.IntegerChoices):
        FACILE = 1, _("Facile")
        MOYENNE = 2, _("Moyenne")
        DIFFICILE = 3, _("Difficile")

    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_("Utilisateur"))
    titre = models.CharField(max_length=100)
    portion = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    typeRecette = models.ForeignKey(TypeRecette, on_delete=models.CASCADE, verbose_name=_("Type de recette"))
    image = models.ImageField(upload_to=path_and_rename, blank=True, null=True,)
    conseil = models.TextField(blank=True, null=True)
    # page d'origine d'une recette importée (Marmiton...) : on cite toujours la source
    source = models.URLField(max_length=500, blank=True, null=True)
    # Durées en minutes, vides si non renseignées ; le total est calculé (voir temps_total)
    tempsPreparation = models.PositiveIntegerField(blank=True, null=True, validators=[MaxValueValidator(DUREE_MAX_MINUTES)])
    tempsCuisson = models.PositiveIntegerField(blank=True, null=True, validators=[MaxValueValidator(DUREE_MAX_MINUTES)])
    tempsRepos = models.PositiveIntegerField(blank=True, null=True, validators=[MaxValueValidator(DUREE_MAX_MINUTES)])
    cout = models.PositiveSmallIntegerField(choices=Cout.choices, blank=True, null=True)
    difficulte = models.PositiveSmallIntegerField(choices=Difficulte.choices, blank=True, null=True)

    class Meta:
        db_table = 'recette'
        constraints = [models.UniqueConstraint(fields=['titre', 'typeRecette'], name='UniciteRecetteTypeRecetteParUtilisateur')]
        verbose_name = "recette"
        verbose_name_plural = "recettes"
    
    def __str__(self):
        return self.titre

    @property
    def temps_total(self):
        """Somme des durées renseignées, None si aucune ne l'est."""
        durees = [d for d in (self.tempsPreparation, self.tempsCuisson, self.tempsRepos) if d is not None]
        return sum(durees) if durees else None

    def durees_formatees(self):
        """Pour le PDF : [('Préparation', '15 min'), ...] des durées renseignées, total compris."""
        durees = [(_("Préparation"), self.tempsPreparation), (_("Cuisson"), self.tempsCuisson), (_("Repos"), self.tempsRepos)]
        lignes = [(libelle, formater_duree(d)) for libelle, d in durees if d]
        if len(lignes) > 1:
            lignes.append((_("Total"), formater_duree(self.temps_total)))
        return lignes

    def image_preview(self):
        if self.image:
            return format_html('<img src="{}" style="width: 100px; height: auto; border-radius: 5px;" />', self.image.url)
        return "Pas d'image"
    
    image_preview.short_description = 'Aperçu'


register_image_cleanup(Recette, 'image')
   
    
class Rayon(models.Model):
    """Rayon du magasin : la liste de courses suit l'ordre de parcours (noOrdre)."""
    nom = models.CharField(max_length=50, unique=True)
    noOrdre = models.IntegerField(default=0)

    class Meta:
        db_table = 'rayon'
        verbose_name = "rayon"
        verbose_name_plural = "rayons"
        ordering = ['noOrdre', 'nom']

    def __str__(self):
        return self.nom


class Produit(models.Model):
    nom = models.TextField(unique=True)
    rayon = models.ForeignKey(Rayon, on_delete=models.SET_NULL, blank=True, null=True)
    # sel, huile, épices... : en principe déjà à la maison, listés à part ("à vérifier dans le placard")
    placard = models.BooleanField(default=False)
    nomPluriel =  models.TextField()
    produitDeBase = models.ForeignKey('self', on_delete=models.PROTECT, verbose_name=_("Produit de base"),blank=True,null=True)
    determinant =  models.CharField(max_length=5, blank=True, null=True)
    # ratio avec le produit de base : "1 gousse (d'ail) = 1 cc (d'ail haché)", "1 (citron) = 40 ml (de jus)".
    # Unité vide = sans unité (pièce). Sans ratio : 1 pour 1, dans la même unité.
    ratioQuantiteBase = models.DecimalField(_("Quantité de base"), max_digits=9, decimal_places=2, blank=True, null=True)
    ratioUniteBase = models.ForeignKey('Unite', on_delete=models.PROTECT, verbose_name=_("Unité de base"), blank=True, null=True, related_name='+')
    ratioQuantite = models.DecimalField(_("= quantité de ce produit"), max_digits=9, decimal_places=2, blank=True, null=True)
    ratioUnite = models.ForeignKey('Unite', on_delete=models.PROTECT, verbose_name=_("Unité de ce produit"), blank=True, null=True, related_name='+')
    # propriétés physiques : convertir volume <-> poids <-> pièces ("1 cs de sucre" -> 15 g, "1 oignon" -> 150 g)
    densite = models.DecimalField(_("Densité (g/ml)"), max_digits=7, decimal_places=3, blank=True, null=True)
    poidsPiece = models.DecimalField(_("Poids d'une pièce (g)"), max_digits=9, decimal_places=2, blank=True, null=True)
    # unité dans laquelle la liste de courses exprime le total : g (poids), ml (volume), pièce, gousse...
    # Vide : pas de conversion entre familles d'unités, chaque famille reste sur sa ligne.
    uniteAchat = models.ForeignKey('Unite', on_delete=models.PROTECT, verbose_name=_("Unité d'achat"), blank=True, null=True, related_name='+')

    class Meta:
        db_table = 'produit'
        verbose_name = "produit"
        verbose_name_plural = "produits"
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(ratioQuantiteBase__isnull=True, ratioQuantite__isnull=True)
                    | Q(ratioQuantiteBase__gt=0, ratioQuantite__gt=0)
                ),
                name="produit_ratio_complet",
            ),
        ]

    def __str__(self):
        return self.nom

    def ratio_texte(self):
        if self.ratioQuantiteBase is None or not self.produitDeBase_id:
            return ""
        base = f"{self.ratioQuantiteBase.normalize():f} {self.ratioUniteBase or ''}".strip()
        derive = f"{self.ratioQuantite.normalize():f} {self.ratioUnite or ''}".strip()
        return f"{base} {self.produitDeBase} = {derive} {self.nom}"

    ratio_texte.short_description = 'Ratio'

    def clean(self):
        super().clean()
        if (self.ratioQuantiteBase is None) != (self.ratioQuantite is None):
            raise ValidationError(_("Le ratio demande les deux quantités (base et produit)."))
        if self.ratioQuantiteBase is not None and not self.produitDeBase_id:
            raise ValidationError({"produitDeBase": _("Un ratio n'a de sens qu'avec un produit de base.")})

class Unite(models.Model):
    class Dimension(models.TextChoices):
        MASSE = 'masse', _("Masse (base : g)")
        VOLUME = 'volume', _("Volume (base : ml)")
        PIECE = 'piece', _("Pièce")
        LONGUEUR = 'longueur', _("Longueur (base : cm)")
        # gousse, botte, tranche... : leur valeur dépend du produit (ProduitMesure)
        VAGUE = 'vague', _("Mesure propre au produit (gousse, botte...)")

    code = models.CharField(max_length=10)
    pluriel = models.CharField(max_length=15, blank=True, default='')  # "gousses" ; vide si identique au code (g, ml...)
    description = models.TextField()
    # dimension + facteur (vers l'unité de base de la dimension) permettent d'additionner 200 g et 0,5 kg
    dimension = models.CharField(max_length=10, choices=Dimension.choices, default=Dimension.VAGUE)
    facteur = models.DecimalField(max_digits=12, decimal_places=4, blank=True, null=True)
    # borne / unité supérieure : quand passer à l'unité d'affichage suivante (1000 g -> kg)
    borneSuperieur = models.IntegerField(blank=True, null=True)
    uniteSuperieur = models.ForeignKey(
        'self', on_delete=models.PROTECT,
        verbose_name=_("Unité superieur"), blank=True, null=True
    )

    class Meta:
        db_table = 'unite'
        verbose_name = "unité"
        verbose_name_plural = "unités"
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(borneSuperieur__isnull=True, uniteSuperieur__isnull=True)
                    | Q(borneSuperieur__isnull=False, uniteSuperieur__isnull=False)
                ),
                name="unite_borne_et_unite_superieure_ensemble",
            ),
            models.CheckConstraint(
                condition=Q(dimension='vague') | Q(facteur__isnull=False),
                name="unite_facteur_obligatoire_si_convertible",
            ),
        ]

    def __str__(self):
        return self.code

    def clean(self):
        super().clean()
        if self.pk and self.uniteSuperieur_id == self.pk:
            raise ValidationError(
                {"uniteSuperieur": _("Une unité ne peut pas être sa propre unité supérieure.")}
            )
        if self.uniteSuperieur and self.uniteSuperieur.dimension != self.dimension:
            raise ValidationError(
                {"uniteSuperieur": _("L'unité supérieure doit avoir la même dimension.")}
            )


class ProduitMesure(models.Model):
    """Valeur d'une mesure propre au produit : "ail · 1 gousse = 5 g", "poireau · 1 botte = 3 (pièces)"."""
    produit = models.ForeignKey(Produit, on_delete=models.CASCADE, related_name='mesures')
    unite = models.ForeignKey(Unite, on_delete=models.PROTECT, related_name='+', limit_choices_to={'dimension': 'vague'})
    quantite = models.DecimalField(max_digits=9, decimal_places=2)
    # unité de la quantité ci-dessus (g, ml, cm...) ; vide = pièces
    uniteReference = models.ForeignKey(Unite, on_delete=models.PROTECT, related_name='+', blank=True, null=True,
                                       limit_choices_to=~Q(dimension='vague'))

    class Meta:
        db_table = 'produit_mesure'
        verbose_name = "mesure du produit"
        verbose_name_plural = "mesures du produit"
        constraints = [models.UniqueConstraint(fields=['produit', 'unite'], name='UniciteMesureParProduit')]

    def __str__(self):
        return f"1 {self.unite} de {self.produit} = {self.quantite.normalize():f} {self.uniteReference or 'pièce(s)'}"


class Ingredient(models.Model):
    recette = models.ForeignKey(Recette,on_delete= models.CASCADE, verbose_name=_("Recette"))
    noOrdre = models.IntegerField()  
    isSection = models.BooleanField(default=False) 
    quantite = models.DecimalField(max_digits=9, decimal_places=2, blank=True, null=True)
    nom = models.TextField(blank=True,null=True)
    unite  = models.ForeignKey(Unite, on_delete=models.PROTECT, blank=True, null=True)
    produit = models.ForeignKey(Produit, on_delete=models.PROTECT, blank=True, null=True)
    # "haché", "émincé", "fondu"... : même produit acheté, préparé autrement
    preparation = models.CharField(max_length=50, blank=True, default='')

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
    


class SiteImport(models.Model):
    """Site dont on peut importer les recettes (liste blanche, gérée dans l'admin).
    Seules les pages de ces domaines sont téléchargées par le serveur (protection SSRF, voir import_web.py)."""
    nom = models.CharField(max_length=50)
    # "marmiton.org" : les sous-domaines (www.marmiton.org) sont acceptés aussi
    domaine = models.CharField(max_length=100, unique=True, help_text=_("Sans http:// ni www. ; ex. marmiton.org"))
    url = models.URLField(help_text=_("Page d'accueil, ouverte depuis la fenêtre d'import"))
    actif = models.BooleanField(default=True)

    class Meta:
        db_table = 'site_import'
        verbose_name = "site d'import"
        verbose_name_plural = "sites d'import"
        ordering = ['nom']

    def __str__(self):
        return self.nom

    def clean(self):
        # "https://www.Marmiton.org/" -> "marmiton.org"
        domaine = (self.domaine or '').strip().lower()
        domaine = re.sub(r'^[a-z]+://', '', domaine).split('/')[0]
        domaine = re.sub(r'^www\.', '', domaine).rstrip('.')
        if not re.fullmatch(r'(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z]{2,}', domaine):
            raise ValidationError({'domaine': _("Nom de domaine invalide (ex. marmiton.org).")})
        self.domaine = domaine


class ImportVideo(models.Model):
    """
    Import d'une recette depuis une vidéo (TikTok...) : trop long pour une requête (modèle de langage local),
    traité en arrière-plan ; le client interroge le statut jusqu'à la fin.
    """
    class Statut(models.TextChoices):
        ATTENTE = 'attente', _("En attente")
        EN_COURS = 'en_cours', _("En cours")
        TERMINE = 'termine', _("Terminé")
        ERREUR = 'erreur', _("Erreur")

    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name=_("Utilisateur"))
    url = models.URLField(max_length=500)
    typeRecette = models.ForeignKey(TypeRecette, on_delete=models.CASCADE, verbose_name=_("Type de recette"))
    importerImage = models.BooleanField(default=True)
    statut = models.CharField(max_length=10, choices=Statut.choices, default=Statut.ATTENTE)
    recette = models.ForeignKey(Recette, on_delete=models.SET_NULL, blank=True, null=True)
    erreur = models.TextField(blank=True, default='')
    creeLe = models.DateTimeField(auto_now_add=True)
    majLe = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'import_video'
        verbose_name = "import vidéo"
        verbose_name_plural = "imports vidéo"
        ordering = ['-creeLe']

    def __str__(self):
        return f"{self.url} ({self.get_statut_display()})"


class EtatClaude(models.Model):
    """
    État de l'API Claude (structuration des recettes vidéo), une seule ligne.
    En panne (clé invalide, crédit épuisé, erreurs répétées...) : un e-mail d'alerte part une fois, l'API n'est plus
    appelée qu'une fois par quart d'heure pour voir si elle refonctionne ; l'import vidéo est suspendu en attendant.
    """
    enPanne = models.BooleanField(default=False)
    raison = models.TextField(blank=True, default='')
    depuis = models.DateTimeField(blank=True, null=True)
    derniereTentative = models.DateTimeField(blank=True, null=True)
    # erreurs passagères (surcharge, réseau...) d'affilée : au-delà d'un seuil, c'est une panne
    echecsTemporaires = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'etat_claude'
        verbose_name = "état de l'API Claude"
        verbose_name_plural = "état de l'API Claude"

    def __str__(self):
        return f"En panne depuis le {self.depuis:%d/%m/%Y %H:%M}" if self.enPanne else "Fonctionne"

    @classmethod
    def obtenir(cls):
        return cls.objects.get_or_create(pk=1)[0]
