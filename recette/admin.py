from django.contrib import admin
from django.db.models import Count, Sum
from django.utils import timezone
import recette.models

class SynonymeInline(admin.TabularInline):
    model = recette.models.Synonyme
    extra = 1
    fields = ('texte',)
    verbose_name_plural = "Synonymes : autres façons de l'écrire (« poireaux », « petit poireau »…)"


class EquivalenceInline(admin.TabularInline):
    model = recette.models.Equivalence
    fk_name = 'produit'
    extra = 1
    fields = ('quantite', 'unite', 'quantiteCible', 'uniteCible', 'produitCible')
    autocomplete_fields = ('produitCible',)
    verbose_name_plural = ("Équivalences : 1 ml = 1,4 g (densité) · 1 (pièce) = 150 g · 1 gousse = 5 g · "
                           "40 ml = 1 (pièce) de citron (dérivé → produit de base). Unité vide = pièce")


@admin.register(recette.models.SiteImport)
class SiteImportAdmin(admin.ModelAdmin):
    """Liste blanche des sites d'import : seules leurs pages sont téléchargées par le serveur."""
    list_display = ('nom', 'domaine', 'url', 'actif')
    list_editable = ('actif',)
    search_fields = ('nom', 'domaine')


@admin.register(recette.models.Produit)
class ProduitAdmin(admin.ModelAdmin):
    list_display = ('nom', 'nomPluriel', 'rayon', 'placard', 'uniteAchat', 'produitDeBase', 'nb_equivalences', 'statut', 'source')
    list_editable = ('rayon', 'placard', 'uniteAchat', 'statut')
    list_filter = ('statut', 'source', 'rayon', 'placard', 'uniteAchat')
    inlines = [SynonymeInline, EquivalenceInline]
    readonly_fields = ['id']
    list_per_page = 50
    search_fields = ('nom', 'synonymes__texte')
    ordering = ('nom',)
    autocomplete_fields = ('produitDeBase',)
    actions = ['valider']
    fieldsets = (
        (None, {'fields': ('id', 'nom', 'nomPluriel', 'determinant', 'rayon', 'placard', ('statut', 'source'))}),
        ('Achat', {
            'fields': ('uniteAchat', 'produitDeBase'),
            'description': "Unité d'achat : celle de la liste de courses (g, ml, pièce, gousse…). "
                           "Produit de base : ce qu'on achète pour un dérivé (jus de citron → citron).",
        }),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(nb_eq=Count('equivalences', distinct=True))

    @admin.display(description="Équivalences", ordering='nb_eq')
    def nb_equivalences(self, obj):
        return obj.nb_eq or ''

    @admin.action(description="Valider les produits sélectionnés")
    def valider(self, request, queryset):
        n = queryset.update(statut=recette.models.Produit.Statut.VALIDE)
        self.message_user(request, f"{n} produit(s) validé(s).")


@admin.register(recette.models.IngredientSansProduit)
class IngredientSansProduitAdmin(admin.ModelAdmin):
    """
    Lignes de recettes dont l'ingrédient n'est pas reconnu : choisir le produit dans la liste et enregistrer.
    Le texte devient aussi un synonyme du produit, pour que les prochains imports le reconnaissent.
    """
    list_display = ('nom', 'quantite', 'unite', 'recette', 'produit')
    list_editable = ('produit',)
    autocomplete_fields = ('produit',)
    search_fields = ('nom', 'recette__titre')
    list_per_page = 50

    def get_queryset(self, request):
        return super().get_queryset(request).filter(isSection=False, produit__isnull=True).select_related('recette', 'unite')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        texte = (obj.nom or '').strip()
        if obj.produit_id and texte and len(texte) <= 200:
            cle = recette.models.normaliser_nom(texte)
            if cle != recette.models.normaliser_nom(obj.produit.nom) and not recette.models.Synonyme.objects.filter(cle=cle).exists():
                recette.models.Synonyme.objects.create(texte=texte, produit=obj.produit)


@admin.register(recette.models.Rayon)
class RayonAdmin(admin.ModelAdmin):
    list_display = ('nom', 'noOrdre')
    list_editable = ('noOrdre',)
    ordering = ('noOrdre',)

@admin.register(recette.models.Unite)
class UniteAdmin(admin.ModelAdmin):
    list_display = ('id','code','pluriel','description', 'dimension', 'facteur', 'uniteSuperieur', 'borneSuperieur')
    list_filter = ('dimension',)
    readonly_fields =[ 'id',]
    list_per_page = 20
    search_fields = ('code',)
    ordering = ('id',)

@admin.register(recette.models.Recette)
class RecetteAdmin(admin.ModelAdmin):
 
    list_display = ( 'titre', 'portion', 'typeRecette', 'cout', 'difficulte')
    readonly_fields =[ 'id','image_preview']
    list_filter = ('typeRecette','user', 'cout', 'difficulte')
    list_per_page = 20
    search_fields = ('titre',)
    ordering = ('titre', )


@admin.register(recette.models.Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ( 'produit','quantite','unite',  'isSection', 'nom', 'recette')
    readonly_fields =[ 'id',]
    list_per_page = 20
    search_fields = ['nom', 'produit__nom','recette__titre']
    list_filter = ('isSection','recette__user',)
    ordering = ('recette', 'noOrdre')
    raw_id_fields = ('produit',)

@admin.register(recette.models.Preparation)
class PreparationAdminTopic(admin.ModelAdmin):
    list_display = ( 'noOrdre','__str__', 'isSection' ,'recette')
    readonly_fields =[ 'id',]
    list_per_page = 20
    ordering = ('recette', 'noOrdre')


def _dollars(valeur):
    """0.0025 -> "0,0025 $" (format de l'admin, en français)."""
    return '—' if valeur is None else f"{valeur:.4f} $".replace('.', ',')


class AppelIAInline(admin.TabularInline):
    model = recette.models.AppelIA
    extra = 0
    can_delete = False
    fields = ('date', 'etape', 'nbImages', 'tokensEntree', 'tokensSortie', 'cout', 'dureeMs', 'statut')
    readonly_fields = fields
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(recette.models.ImportVideo)
class ImportVideoAdmin(admin.ModelAdmin):
    """Suivi des imports TikTok (traités en arrière-plan) : utile pour voir pourquoi un import a échoué."""
    list_display = ('url', 'user', 'statut', 'recette', 'cout_ia', 'creeLe')
    list_filter = ('statut', 'creeLe')
    readonly_fields = ('user', 'url', 'typeRecette', 'importerImage', 'statut', 'recette', 'erreur', 'creeLe', 'majLe')
    inlines = [AppelIAInline]

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(total_ia=Sum('appelsIA__cout'))

    @admin.display(description="Coût IA", ordering='total_ia')
    def cout_ia(self, obj):
        return _dollars(obj.total_ia)


@admin.register(recette.models.AppelIA)
class AppelIAAdmin(admin.ModelAdmin):
    """Tous les appels à l'API Claude, avec leur coût ; total de la sélection en haut de la liste."""
    list_display = ('date', 'etape', 'importVideo', 'user', 'modele', 'nbImages', 'tokensEntree', 'tokensSortie',
                    'cout_affiche', 'duree', 'statut')
    # filtre par date en colonne (date_hierarchy demande les fuseaux horaires installés dans MySQL)
    list_filter = ('date', 'statut', 'etape', 'modele')
    search_fields = ('importVideo__url', 'user__email', 'erreur')
    readonly_fields = [f.name for f in recette.models.AppelIA._meta.fields]
    change_list_template = 'admin/recette/appelia/change_list.html'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    @admin.display(description="Coût", ordering='cout')
    def cout_affiche(self, obj):
        return _dollars(obj.cout)

    @admin.display(description="Durée", ordering='dureeMs')
    def duree(self, obj):
        return f"{obj.dureeMs / 1000:.1f} s"

    def changelist_view(self, request, extra_context=None):
        reponse = super().changelist_view(request, extra_context)
        try:
            selection = reponse.context_data['cl'].queryset
        except (AttributeError, KeyError):
            return reponse  # redirection (filtre invalide...)
        maintenant = timezone.localtime()
        debut_mois = maintenant.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        reponse.context_data['totaux'] = {
            'selection': selection.aggregate(nombre=Count('id'), cout=Sum('cout'), entree=Sum('tokensEntree'), sortie=Sum('tokensSortie')),
            'mois': recette.models.AppelIA.objects.filter(date__gte=debut_mois).aggregate(nombre=Count('id'), cout=Sum('cout')),
            'total': recette.models.AppelIA.objects.aggregate(nombre=Count('id'), cout=Sum('cout')),
        }
        return reponse



@admin.register(recette.models.EtatClaude)
class EtatClaudeAdmin(admin.ModelAdmin):
    """API Claude (import TikTok) : en panne ou non, pourquoi, et bouton pour revérifier après avoir rechargé le crédit."""
    list_display = ('__str__', 'raison', 'derniereTentative')
    readonly_fields = ('enPanne', 'raison', 'depuis', 'derniereTentative', 'echecsTemporaires')
    actions = ['reverifier']

    def has_add_permission(self, request):
        return False

    def get_queryset(self, request):
        # la ligne unique existe toujours, pour pouvoir lancer la vérification avant le premier import
        recette.models.EtatClaude.obtenir()
        return super().get_queryset(request)

    @admin.action(description="Revérifier l'API Claude maintenant")
    def reverifier(self, request, queryset):
        from django.contrib import messages
        from recette.import_ia import verifier_maintenant
        ok, message = verifier_maintenant()
        self.message_user(request, message, messages.SUCCESS if ok else messages.ERROR)
