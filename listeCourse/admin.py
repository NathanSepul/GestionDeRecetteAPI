from django.contrib import admin
import listeCourse.models


class ListeCourseRecetteInline(admin.TabularInline):
    model = listeCourse.models.ListeCourseRecette
    raw_id_fields = ('recette',)
    extra = 0


@admin.register(listeCourse.models.ListeCourse)
class ListeCourseAdmin(admin.ModelAdmin):
    list_display = ('nom', 'user', 'dateModification')
    list_filter = ('user',)
    readonly_fields = ('dateCreation', 'dateModification')
    inlines = [ListeCourseRecetteInline]
