from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractUser
from django.urls import reverse
from django.contrib.staticfiles.storage import staticfiles_storage
from django.utils.translation import gettext_lazy as _
import datetime
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from rest_framework.authtoken.models import Token

# Custom Auth
# https://docs.djangoproject.com/fr/3.2/topics/auth/customizing/#a-full-example


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
    LANGUAGES = {
        ('fr', 'Francais'),
        ('en', 'Anglais'),
    }

    email = models.EmailField(verbose_name=_( "Adresse Email"), max_length=255, unique=True,)
    first_name = models.CharField(verbose_name=_("Prénom"), max_length=255,)
    last_name = models.CharField(verbose_name=_("Nom"), max_length=255,)
    language = models.CharField( max_length=8, choices=LANGUAGES, default="fr" )


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
