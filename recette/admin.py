from django.contrib import admin
import recette.models

@admin.register(recette.models.Produit)
class ProduitAdmin(admin.ModelAdmin):
    list_display = ( 'nom','nomPluriel','produitDeBase')
    readonly_fields =[ 'id',]
    list_per_page = 20
    search_fields = ('nom',)
    ordering = ('nom',)
    raw_id_fields = ('produitDeBase',)

@admin.register(recette.models.Unite)
class UniteAdmin(admin.ModelAdmin):
    list_display = ('id','code','description')
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
