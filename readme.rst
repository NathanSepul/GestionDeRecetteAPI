======================
Configuration de l'API
======================

1. Base de données
Créez une base de données MySQL nommée ``recette``.

.. code-block:: MySQL

    CREATE DATABASE recette;

|

2. Création de l'environnement virtuel

La création de votre environnement virtuel peut être réalisée n'importe où sur votre
ordinateur. Je vous recommande de créer un dossier "virtual" dans lequel vous
pourrez créer vos différents environnements virtuels afin de les centraliser.

.. code-block:: sh

    mkdir venv_gestionDeRecette
    cd venv_gestionDeRecette
    python -m venv .

|

3. Activation de l'environnement virtuel

.. code-block:: sh

    cd venv_gestionDeRecette
    source ./bin/activate

|

4. Installation des dépendances

Depuis la racine du dossier de l'API ``gestionDeRecette``, exécutez la commande suivante pour installer les packages requis :

.. code-block:: sh

    # en développement (ajoute django-extensions)
    pip install -r requirements-dev.txt

    # en production
    pip install -r requirements.txt

|

5. Configuration des variables d'environnement

Copiez ``.env.example`` en ``.env`` à la racine du dossier de l'API et complétez-le.
Le fichier indique la commande pour générer ``SECRET_KEY``.

|

6. Création des tables

.. code-block:: sh

    ./manage.py migrate
    # table du cache (compteurs de limitation des requêtes : login, mot de passe oublié, import)
    ./manage.py createcachetable

|

7. Créer un compte super utilisateur
Utilisez la commande suivante pour créer un compte super utilisateur :

.. code-block:: sh

    ./manage.py createsuperuser

|

8. Lancer le projet
Utilisez la commande suivante pour démarrer le serveur de développement

.. code-block:: sh

    ./manage.py runserver

|

9. Une fois que l'API a été lancée avec succès, vous pouvez accéder à certaines fonctionnalités :

* Documentation de l'API : http://localhost:8000/api/swagger/
* Interface d'administration : http://localhost:8000/admin/. Vous pouvez vous connecter en utilisant le compte super utilisateur créé précédemment.

|

10. Tests

.. code-block:: sh

    ./manage.py test

|

=========================
Déploiement (production)
=========================

Le ``.env`` de prod contient ``DEBUG=off`` et ``STATIC_ROOT`` (dossier servi par Nginx), voir ``.env.example``.

.. code-block:: sh

    git pull
    pip install -r requirements.txt
    ./manage.py migrate
    ./manage.py createcachetable   # ne fait rien si la table existe déjà
    ./manage.py collectstatic --noinput
    sudo systemctl restart gunicornRecette

Nginx sert directement ``/static/`` et ``/media/`` ; ``/api`` et ``/admin`` passent par Gunicorn.

|

Import depuis TikTok
--------------------

La recette est mise en forme par l'API Claude, qui lit toujours la description de la vidéo (yt-dlp) :

* description qui contient visiblement la recette (« Ingrédients : », plusieurs quantités) : Claude la lit seule,
  sans télécharger la vidéo (~5 s) ;
* sinon, ou si la recette obtenue est incomplète (recette dite à l'oral ou écrite à l'écran) : la vidéo est téléchargée,
  la voix transcrite sur le serveur par Whisper (faster-whisper) et une image prise toutes les 2 secondes ;
  Claude reçoit le tout avec la description. Compter environ 1 minute (surtout la transcription).

Il faut ``ANTHROPIC_API_KEY`` dans le ``.env`` (sans clé, l'import TikTok est désactivé) : clé sur
https://console.anthropic.com (crédit prépayé, de l'ordre de 0,05 à 0,2 centime par recette avec Claude Haiku).

Le modèle Whisper (``WHISPER_MODELE``, ``small`` par défaut, ~500 Mo) est téléchargé au premier import. Pour le faire
à l'avance (et vérifier que l'utilisateur de Gunicorn peut écrire dans ``~/.cache/huggingface``) :

.. code-block:: sh

    python -c "from faster_whisper import WhisperModel; WhisperModel('small', device='cpu', compute_type='int8')"

Le modèle reste en mémoire dans le processus Gunicorn (~500 Mo) : garder un seul worker (``-w 1 --threads 4``).

L'import tourne en arrière-plan, une vidéo à la fois par processus (suivi dans l'admin : « Imports vidéo »).

Surveillance de l'API Claude (admin : « État de l'API Claude ») : clé invalide, crédit épuisé, modèle retiré ou
erreurs répétées déclenchent un e-mail à ``ALERTE_EMAIL`` (à défaut ``DEBUG_EMAIL``), une fois par panne. Pendant la panne,
l'import TikTok est suspendu et l'API est réessayée toutes les 15 minutes ; un e-mail signale son retour.
Après avoir rechargé le crédit, l'action « Revérifier l'API Claude maintenant » de l'admin rétablit le service tout de suite.

TikTok change souvent son site : si les imports échouent, mettre à jour yt-dlp (``pip install -U yt-dlp``,
puis reporter la version dans ``requirements.txt``).
