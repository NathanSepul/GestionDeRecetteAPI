from django.contrib import admin
import recette.models

@admin.register(recette.models.Produit)
class ProduitAdmin(admin.ModelAdmin):
    list_display = ( 'nom','nomPluriel','produitDeBase', 'ratio_texte')
    readonly_fields =[ 'id', 'ratio_texte']
    list_per_page = 20
    search_fields = ('nom',)
    ordering = ('nom',)
    raw_id_fields = ('produitDeBase',)
    fieldsets = (
        (None, {'fields': ('id', 'nom', 'nomPluriel', 'determinant')}),
        ('Produit de base', {
            'fields': ('produitDeBase', ('ratioQuantiteBase', 'ratioUniteBase'), ('ratioQuantite', 'ratioUnite'), 'ratio_texte'),
            'description': "Ex. 1 gousse d'ail = 1 cc d'ail haché. Sans ratio : 1 pour 1, dans la même unité.",
        }),
    )

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
 
    list_display = ( 'titre', 'portion', 'typeRecette')
    readonly_fields =[ 'id','image_preview']
    list_filter = ('typeRecette','user')
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
