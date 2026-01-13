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
    
    pip install -r requirements.txt

|

5. Configuration des variables d'environnement

Ajoutez un fichier ``.env`` à la racine du dossier de l'API en incluant les informations suivantes :

.. code-block:: txt

    DEBUG=on
    SECRET_KEY=''

    # DB
    DB_USER=
    DB_PASSWORD=
    DB_DATABASE=recette
    DB_HOST=localhost
    DB_PORT=

    DEBUG_EMAIL=''
    DEFAULT_FROM_EMAIL='''
    EMAIL_HOST_USER=''
    EMAIL_HOST_PASSWORD=''
    EMAIL_HOST=''
    EMAIL_PORT=

    APP_NAME='MesRecettes'

|

6. Creer un compte super utilisateur
Utilisez la commande suivante pour créer un compte super utilisateur :

.. code-block:: sh

    ./manage.py createsuperuser

|

7. Lancer le projet 
Utilisez la commande suivante pour démarrer le serveur de développement

.. code-block:: sh
    
    ./manage.py runserver

8. Une fois que l'API a été lancée avec succès, vous pouvez accéder à certaines fonctionnalités :

* Documentation de l'API : Ouvrez un navigateur web et accédez à l'URL http://localhost:8000 pour accéder à la documentation de l'API.
* Interface d'administration : Pour gérer votre application et ses données, accédez à http://localhost:8000/admin. Vous pouvez vous connecter en utilisant le compte super utilisateur créé précédemment.
