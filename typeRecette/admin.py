from django.contrib import admin
import typeRecette.models


@admin.register(typeRecette.models.TypeRecette)
class TypeRecetteAdminTopic(admin.ModelAdmin):
    list_display = ('noOrdre', 'type',)
    # list_filter = ("noOrdre", )
    # list_per_page = 20
    # search_fields = ('type',)
    # ordering = ('type', )