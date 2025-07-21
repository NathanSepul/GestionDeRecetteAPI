===================
Gestion de recette
===================

1. creation virtual env 

.. code-block:: sh
    
    mkdir gestionDeRecette
    cd gestionDeRecette
    python -m venv .  

|

2. activate virtual env

.. code-block:: sh
    
    cd gestionDeRecette
    source ./bin/activate

|

3. Installation packages

.. code-block:: sh
    
    pip install -r requirements.txt

|


4. Configuration des variables d'environnement

Ajoutez un fichier ``.env`` à la racine du dossier de l'API en incluant les informations suivantes :

.. code-block:: txt

    DEBUG=True

    # DB
    DB_USER= 
    DB_PASSWORD= 
    DB_DATABASE=isl_forum
    DB_HOST= 
    DB_PORT=

|

5. start project

.. code-block:: sh
    
    ./manage.py runserver