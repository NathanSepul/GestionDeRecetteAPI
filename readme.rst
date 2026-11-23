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
