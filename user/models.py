import os
import uuid
from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractUser
from django.contrib.staticfiles.storage import staticfiles_storage
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _
from django.utils.html import format_html
from django.db.models.signals import post_delete, pre_save

# Custom Auth
# https://docs.djangoproject.com/fr/3.2/topics/auth/customizing/#a-full-example

def path_and_rename(instance, filename):
        ext = filename.split('.')[-1]
        unique_id = uuid.uuid4().hex[:8]
        return os.path.join('avatars/', f"{unique_id}.{ext}")
    
class UserManager(BaseUserManager):
    """Define a model manager for User model with no username field."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        """Create and save a User with the given email and password."""
        if not email:
            raise ValueError('The given email must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)

        import typeRecette.models
        typeRecette.models.TypeRecette.objects.create( user=user,  noOrdre=1, type="Entrée")
        typeRecette.models.TypeRecette.objects.create( user=user,  noOrdre=2, type="Plat")
        typeRecette.models.TypeRecette.objects.create( user=user,  noOrdre=3, type="Dessert")

        import tag.models
        tag.models.Tag.objects.create( user=user, tag="Poisson", red=81, green=88, blue=192, opacite=210)
        tag.models.Tag.objects.create( user=user, tag="Végétarien",  red=105, green=170, blue=0, opacite=210)
        tag.models.Tag.objects.create( user=user, tag="Porc",  red=255, green=47, blue=0, opacite=82)
        tag.models.Tag.objects.create( user=user, tag="Poulet",  red=255, green=0, blue=4, opacite=255)
        
        return user

    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular User with the given email and password."""
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        """Create and save a SuperUser with the given email and password."""
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    LANGUAGES = (
        ('fr', 'Francais'),
        ('en', 'Anglais'),
    )

    email = models.EmailField(verbose_name=_( "Adresse Email"), max_length=255, unique=True,)
    first_name = models.CharField(verbose_name=_("Prénom"), max_length=255,)
    last_name = models.CharField(verbose_name=_("Nom"), max_length=255,)
    language = models.CharField( max_length=8, choices=LANGUAGES, default="fr" )
    following = models.ManyToManyField('self', blank=True, symmetrical=False,related_name='followers')
    avatar = models.ImageField(upload_to=path_and_rename, blank=True, null=True,)

    # pour ne pas avoir de username (contrer les valeurs par defaut)
    username = None
    objects = UserManager()

    # faire sort que l'unicité se trouve sur l'email
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', ]

    class Meta:
        db_table = 'user'
        verbose_name = _("Utilisateur")
        verbose_name_plural = _("Utilisateurs")

    def __str__(self):
        return self.email

    def avatar_preview(self):
        if self.avatar:
            return format_html('<img src="{}" style="width: 100px; height: auto; border-radius: 5px;" />', self.avatar.url)
        return "Pas d'image"
    
    avatar_preview.short_description = 'Aperçu'

@receiver(post_delete, sender=User)
def auto_delete_file_on_delete(sender, instance, **kwargs):
    """Supprime le fichier du disque quand la recette est supprimée de la base."""
    if instance.avatar:
        if os.path.isfile(instance.avatar.path):
            os.remove(instance.avatar.path)

@receiver(pre_save, sender=User)
def auto_delete_file_on_change(sender, instance, **kwargs):
    """Supprime l'ancien fichier quand une nouvelle image est téléchargée."""
    if not instance.pk:
        return False

    try:
        old_file = User.objects.get(pk=instance.pk).avatar
    except User.DoesNotExist:
        return False

    new_file = instance.avatar
    if old_file and old_file != new_file:
        if os.path.isfile(old_file.path):
            os.remove(old_file.path)