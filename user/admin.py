from django.contrib import admin
from django.contrib.auth.models import Group
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

import user.models


@admin.register(user.models.User)
class UserAdmin(BaseUserAdmin):

    list_display = ('email', 'first_name', 'last_name', 'is_superuser', 'is_active')
    list_filter = ('is_active','is_superuser')
    readonly_fields = ('last_login', "date_joined")
    list_per_page = 20
    search_fields = ('email', )
    ordering = ('email', )

    fieldsets = (
        ("Identification", {'fields': ('email', 'password')}),

        ('Informations personnelles', {'fields': ( 'first_name', 'last_name','language' )}),

        ('Date importante', {'fields': ('last_login', 'date_joined')}),

        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser',)}),
    )

    add_fieldsets = (
        ("Inscription", {
            'fields': (  'email', 'password1', 'password2', 'first_name', 'last_name',  ),
        }),
    )



   


admin.site.unregister(Group)
