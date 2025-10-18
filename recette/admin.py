from django.contrib import admin
import recette.models
from django.utils.safestring import mark_safe
from django.utils.html import format_html
from typing import Optional
import base64

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
 
    def image_tag(self) -> Optional[str]:
        if self.image:
            # 1. Convertir les données binaires en Base64
            base64_data = base64.b64encode(self.image).decode('utf-8')
            
            # 2. Créer l'URL de données (data URI)
            # Nous supposons que l'image est un JPEG ou que le type MIME est approprié
            data_uri = f'data:image/jpeg;base64,{base64_data}'
            
            # 3. Utiliser format_html pour générer la balise <img>
            return format_html('<img src="{}" style="max-width: 150px; max-height: 150px;" />', data_uri)
        
        return "Pas d'image"

    image_tag.short_description = 'Aperçu de l\'image'

    list_display = ( 'titre', 'portion', 'typeRecette')
    readonly_fields =[ 'id','image_tag']
    list_filter = ('typeRecette',)
    list_per_page = 20
    search_fields = ('titre',)
    ordering = ('titre', )


@admin.register(recette.models.Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ( 'produit','quantite','unite',  'isSection', 'nom', 'recette')
    readonly_fields =[ 'id',]
    list_per_page = 20
    search_fields = ('nom',)
    ordering = ('recette', 'noOrdre')
    raw_id_fields = ('produit',)

@admin.register(recette.models.Preparation)
class PreparationAdminTopic(admin.ModelAdmin):
    list_display = ( 'noOrdre','__str__', 'isSection' ,'recette')
    readonly_fields =[ 'id',]
    list_per_page = 20
    ordering = ('recette', 'noOrdre')
