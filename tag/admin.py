from django.contrib import admin
import tag.models

@admin.register(tag.models.Tag)
class RecetteAdminTopic(admin.ModelAdmin):
    list_display = ( 'tag', 'red' ,'green', 'blue', 'opacite')
    readonly_fields =[ 'id',]
    list_per_page = 20
    search_fields =['tag',]