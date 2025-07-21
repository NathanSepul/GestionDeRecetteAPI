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

3. installation packages

.. code-block:: sh
    
    pip install -r requirements.txt

|

4. lancer le projet (at the root of projet)

.. code-block:: sh
    
    ./manage.py runserver