from django.contrib import admin
import recette.models
from django.utils.safestring import mark_safe

@admin.register(recette.models.Produit)
class ProduitAdmin(admin.ModelAdmin):
    list_display = ( 'nom','nomPluriel')
    readonly_fields =[ 'id',]
    list_per_page = 20
    search_fields = ('nom',)
    ordering = ('nom',)

@admin.register(recette.models.Unite)
class UniteAdmin(admin.ModelAdmin):
    list_display = ('id','code','description')
    readonly_fields =[ 'id',]
    list_per_page = 20
    search_fields = ('code',)
    ordering = ('id',)

@admin.register(recette.models.Recette)
class RecetteAdmin(admin.ModelAdmin):
    def get_image_preview(self, obj):
        if obj.image_as_base64:
            return mark_safe(f'<img src="data:image/jpeg;base64,{obj.image_as_base64}" width="100" />')
        return "No Image"
    
    get_image_preview.short_description = 'Image'

    list_display = ( 'titre', 'portion', 'typeRecette')
    readonly_fields =[ 'id','get_image_preview']
    list_filter = ('typeRecette',)
    list_per_page = 20
    search_fields = ('titre',)
    ordering = ('titre', )


@admin.register(recette.models.Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ( 'noOrdre','quantite', 'nom', 'isSection' ,'recette')
    readonly_fields =[ 'id',]
    list_per_page = 20
    search_fields = ('nom',)
    ordering = ('recette', 'noOrdre')

@admin.register(recette.models.Preparation)
class PreparationAdminTopic(admin.ModelAdmin):
    list_display = ( 'noOrdre','__str__', 'isSection' ,'recette')
    readonly_fields =[ 'id',]
    list_per_page = 20
    ordering = ('recette', 'noOrdre')
