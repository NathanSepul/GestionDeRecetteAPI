from django.contrib import admin
import recette.models

class ProduitMesureInline(admin.TabularInline):
    model = recette.models.ProduitMesure
    extra = 0
    verbose_name_plural = "Mesures propres au produit (ex. 1 gousse = 5 g)"


@admin.register(recette.models.SiteImport)
class SiteImportAdmin(admin.ModelAdmin):
    """Liste blanche des sites d'import : seules leurs pages sont téléchargées par le serveur."""
    list_display = ('nom', 'domaine', 'url', 'actif')
    list_editable = ('actif',)
    search_fields = ('nom', 'domaine')


@admin.register(recette.models.Produit)
class ProduitAdmin(admin.ModelAdmin):
    list_display = ( 'nom','nomPluriel','rayon', 'placard', 'uniteAchat', 'densite', 'poidsPiece', 'produitDeBase', 'ratio_texte')
    list_editable = ('rayon', 'placard', 'uniteAchat', 'densite', 'poidsPiece')
    list_filter = ('rayon', 'placard', 'uniteAchat')
    inlines = [ProduitMesureInline]
    readonly_fields =[ 'id', 'ratio_texte']
    list_per_page = 20
    search_fields = ('nom',)
    ordering = ('nom',)
    raw_id_fields = ('produitDeBase',)
    fieldsets = (
        (None, {'fields': ('id', 'nom', 'nomPluriel', 'determinant', 'rayon', 'placard')}),
        ('Conversions', {
            'fields': ('uniteAchat', 'densite', 'poidsPiece'),
            'description': "Unité d'achat : g, ml, pièce ou une mesure (gousse...). "
                           "Densité : 1 cs de sucre (15 ml) = 15 g -> 1. Poids d'une pièce : 1 oignon = 150 g.",
        }),
        ('Produit de base', {
            'fields': ('produitDeBase', ('ratioQuantiteBase', 'ratioUniteBase'), ('ratioQuantite', 'ratioUnite'), 'ratio_texte'),
            'description': "Ex. 1 gousse d'ail = 1 cc d'ail haché. Sans ratio : 1 pour 1, dans la même unité.",
        }),
    )

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


@admin.register(recette.models.ImportVideo)
class ImportVideoAdmin(admin.ModelAdmin):
    """Suivi des imports TikTok (traités en arrière-plan) : utile pour voir pourquoi un import a échoué."""
    list_display = ('url', 'user', 'statut', 'recette', 'creeLe')
    list_filter = ('statut',)
    readonly_fields = ('user', 'url', 'typeRecette', 'importerImage', 'statut', 'recette', 'erreur', 'creeLe', 'majLe')



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
