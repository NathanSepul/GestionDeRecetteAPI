from django.contrib import admin
import recette.models


@admin.register(recette.models.Recette)
class RecetteAdminTopic(admin.ModelAdmin):
    list_display = ( 'titre', 'portion', 'typeRecette')
    readonly_fields =[ 'id','image']
    list_filter = ('typeRecette',)
    list_per_page = 20
    search_fields = ('titre',)
    ordering = ('titre', )


@admin.register(recette.models.Ingredient)
class RecetteAdminTopic(admin.ModelAdmin):
    list_display = ( 'quantite', 'nom', 'isSection' ,'recette')
    readonly_fields =[ 'id',]
    list_per_page = 20
    search_fields = ('nom',)
    ordering = ('recette', 'noOrdre')

@admin.register(recette.models.Preparation)
class RecetteAdminTopic(admin.ModelAdmin):
    list_display = ( '__str__', 'isSection' ,'recette')
    readonly_fields =[ 'id',]
    list_per_page = 20
    ordering = ('recette', 'noOrdre')
