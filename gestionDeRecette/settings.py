from pathlib import Path
import os
import environ
from datetime import timedelta

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    # set casting, default value
    DEBUG=(bool, False)
)

environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env("SECRET_KEY")

APP_NAME = env('APP_NAME')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env('DEBUG')

if DEBUG :
    ALLOWED_HOSTS = ['*']
else :
    ALLOWED_HOSTS = ['sepul.be', 'www.sepul.be']

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
# 
    'user',
    'typeRecette',
    'recette',
    'tag',
    'appVersion',
    'listeCourse',
#
    'rest_framework',
    'rest_registration',
    'rest_framework_simplejwt',
    # requis pour que BLACKLIST_AFTER_ROTATION invalide réellement les anciens refresh tokens
    'rest_framework_simplejwt.token_blacklist',
    'drf_spectacular',
    'corsheaders',
]

# Outils de dev (requirements-dev.txt) : pas installés en prod
if DEBUG:
    INSTALLED_APPS.append('django_extensions')

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'gestionDeRecette.urls'

# Nécessaire pour que Django fasse confiance au proxy Nginx
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
CSRF_USE_SESSIONS = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
CSRF_TRUSTED_ORIGINS =  ['https://sepul.be', 'https://www.sepul.be']
# Le navigateur n'essaiera plus jamais le HTTP pour sepul.be (sans les sous-domaines : ils hébergent d'autres sites)
SECURE_HSTS_SECONDS = 0 if DEBUG else 31536000

# Le client web (fetch credentials: "include") envoie le cookie HttpOnly du refresh token
CORS_ALLOW_CREDENTIALS = True

if DEBUG :
    CORS_ALLOW_ALL_ORIGINS = True
else :
   CORS_ALLOWED_ORIGINS = [
        "https://sepul.be",
        "https://www.sepul.be",
    ]

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, 'templates')
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]


WSGI_APPLICATION = 'gestionDeRecette.wsgi.application' 


# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': env('DB_DATABASE'),
        'USER': env('DB_USER'),
        'PASSWORD': env('DB_PASSWORD'),
        'HOST': env('DB_HOST'),
        'PORT': env('DB_PORT'),
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'"
        }
    }
}

# Cache en base : partagé entre les 3 workers Gunicorn (le cache mémoire par défaut est propre à chaque worker,
# chaque compteur de limitation de requêtes serait alors multiplié par 3). Table créée par : manage.py createcachetable
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'django_cache',
    }
}

AUTH_USER_MODEL = 'user.User'

# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [

    {
        # minimum 8
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        # au moins une majuscule
        'NAME': 'gestionDeRecette.validators.UppercaseValidator',
    },
    {
        # au moins une minuscule
        'NAME': 'gestionDeRecette.validators.LowercaseValidator',
    },
    # {
    #     # au moins un caractère spécial
    #     'NAME': 'django.contrib.auth.password_validation.SymbolValidator',
    # },
]


# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = 'fr-be'
TIME_ZONE = 'Europe/Brussels'
USE_I18N = True
USE_TZ = True

# Django Emails
EMAIL_BACKEND = 'gestionDeRecette.mail.CustomEmailBackend' 
DEBUG_EMAIL = env('DEBUG_EMAIL')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL')
EMAIL_HOST_USER = env('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD')
EMAIL_HOST = env('EMAIL_HOST')
EMAIL_PORT = env.int('EMAIL_PORT')
EMAIL_USE_TLS = False  
EMAIL_USE_SSL = True 


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

# Par défaut dans le projet ; en prod, STATIC_ROOT est le dossier servi par Nginx (location /static/)
STATIC_ROOT = env('STATIC_ROOT', default=os.path.join(BASE_DIR, 'staticfiles'))
MEDIA_ROOT = env('MEDIA_ROOT', default=os.path.join(BASE_DIR, 'media'))

# Import de recettes depuis une vidéo TikTok (recette/import_video.py, recette/import_ia.py) :
# l'API Claude met en forme la recette (description, voix, texte à l'écran). Clé vide = import TikTok désactivé.
ANTHROPIC_API_KEY = env('ANTHROPIC_API_KEY', default='')
CLAUDE_MODELE = env('CLAUDE_MODELE', default='claude-haiku-5-5')
# Destinataire des alertes (API Claude en panne : crédit épuisé, clé invalide...) ; vide = DEBUG_EMAIL
ALERTE_EMAIL = env('ALERTE_EMAIL', default='')
# Analyse de la vidéo quand sa description ne contient pas la recette (recette/import_media.py)
WHISPER_MODELE = env('WHISPER_MODELE', default='small')
VIDEO_DUREE_MAX = env.int('VIDEO_DUREE_MAX', default=600)

STATIC_URL = 'static/'
MEDIA_URL = 'media/'
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': ('rest_framework.renderers.JSONRenderer',),
    
    'DEFAULT_PAGINATION_CLASS': 'gestionDeRecette.serializer.MyPagination',
    'PAGE_SIZE': 10,

    # 'DEFAULT_PERMISSION_CLASSES': ('rest_framework.permissions.AllowAny',),
    'DEFAULT_PERMISSION_CLASSES': ('rest_framework.permissions.IsAuthenticated',),
    'DEFAULT_AUTHENTICATION_CLASSES': ('rest_framework_simplejwt.authentication.JWTAuthentication',),

    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',

    # Limites appliquées aux vues qui déclarent un throttle_scope (ScopedRateThrottle)
    'DEFAULT_THROTTLE_RATES': {
        'login': '10/min',
        'reset_password': '5/hour',
        'import_url': '30/hour',
    },
    # Derrière Nginx, REMOTE_ADDR vaut l'adresse du proxy : l'IP du client est lue dans X-Forwarded-For.
    # Sans ça, tous les visiteurs partageraient le même compteur.
    'NUM_PROXIES': None if DEBUG else 1,
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'Gestion de recette API',
    'DESCRIPTION': 'Petite application permettant de gerer des recette',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}



REST_REGISTRATION = {
    # Pas d'inscription libre : les comptes sont créés dans l'admin Django
    'REGISTER_FLOW_ENABLED': False,
    'REGISTER_VERIFICATION_ENABLED': False,
    'REGISTER_EMAIL_VERIFICATION_ENABLED': False,
    'RESET_PASSWORD_VERIFICATION_ENABLED': True,

    'RESET_PASSWORD_VERIFICATION_URL': 'https://sepul.be/reset-password-form',

    'VERIFICATION_FROM_EMAIL': 'nathan@sepul.be',

    'RESET_PASSWORD_VERIFICATION_ONE_TIME_USE': True,

    'RESET_PASSWORD_VERIFICATION_EMAIL_TEMPLATES':{
        'subject':  'email/reset_password/subject.txt',
        'text_body':  'email/reset_password/body.txt',
    }
}


# Seules les valeurs qui diffèrent des réglages par défaut de simplejwt
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(days=1),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=8),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "TOKEN_OBTAIN_SERIALIZER": "user.serializer.MyTokenObtainPairSerializer",
}





# Sans config, Django n'écrit pas les erreurs 500 dans la console quand DEBUG=False (gunicorn les récupère via stderr)
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {'class': 'logging.StreamHandler'},
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
}
