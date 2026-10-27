from decimal import Decimal

PIECE = 'piece'


def _unite_info(unite):
    """(dimension, facteur) d'une unité ; sans unité = pièce ("2 oignons")."""
    if unite is None:
        return PIECE, Decimal(1)
    return unite.dimension, unite.facteur


def _unite_affichage(unites_utilisees):
    """La plus petite unité utilisée dans le groupe : on part de là, puis on monte si la quantité le justifie."""
    return min(unites_utilisees, key=lambda u: (_unite_info(u)[1], u is not None))


def _monter_unite(quantite_base, unite, unites_par_id):
    """1500 g -> 1,5 kg : suit uniteSuperieur tant que la quantité atteint borneSuperieur."""
    while unite is not None and unite.uniteSuperieur_id and unite.borneSuperieur:
        quantite = quantite_base / unite.facteur
        superieure = unites_par_id.get(unite.uniteSuperieur_id)
        if superieure is None or superieure.facteur is None or quantite < unite.borneSuperieur:
            break
        unite = superieure
    return unite


def construire_liste_course(ingredients, scaling_factor, unites_par_id):
    """
    Agrège les ingrédients par produit (ou nom libre) et par dimension d'unité :
    200 g + 0,5 kg de beurre -> 700 g ; 1 cs + 1 cc d'huile -> 20 ml.
    Les unités non convertibles (pincée...) ne s'additionnent qu'entre elles.
    Un même produit dans deux dimensions (2 oignons + 150 g d'oignon) reste sur deux lignes.
    """
    groupes = {}

    for ingredient in ingredients:
        unite = ingredient.unite
        dimension, facteur = _unite_info(unite)
        convertible = facteur is not None

        if ingredient.produit_id:
            cle_produit = ('produit', ingredient.produit_id)
        else:
            cle_produit = ('nom', (ingredient.nom or '').strip().lower())
        cle_unite = dimension if convertible else ('unite', unite.id)

        groupe = groupes.setdefault((cle_produit, cle_unite), {
            'produit': ingredient.produit,
            'nom': ingredient.nom if not ingredient.produit_id else None,
            'unites': [],
            'quantite_base': None,  # en unité de base (g, ml, pièce, cm) ou dans l'unité elle-même si non convertible
        })
        if unite not in groupe['unites']:
            groupe['unites'].append(unite)

        if ingredient.quantite is not None:
            quantite = ingredient.quantite * scaling_factor * (facteur if convertible else 1)
            groupe['quantite_base'] = quantite if groupe['quantite_base'] is None else groupe['quantite_base'] + quantite

    # "sel, au goût" sans quantité n'apporte rien si le produit est déjà sur la liste avec une quantité
    produits_avec_quantite = {cle_produit for (cle_produit, _), g in groupes.items() if g['quantite_base'] is not None}
    groupes = {
        cle: g for cle, g in groupes.items()
        if g['quantite_base'] is not None or cle[0] not in produits_avec_quantite
    }

    resultats = []
    for groupe in groupes.values():
        unite = _unite_affichage(groupe['unites'])
        quantite = groupe['quantite_base']
        facteur = _unite_info(unite)[1]

        if quantite is not None and facteur is not None:
            unite = _monter_unite(quantite, unite, unites_par_id)
            quantite = quantite / _unite_info(unite)[1]

        resultats.append({
            'produit': groupe['produit'],
            'nom': groupe['nom'],
            'unite': unite,
            'quantite': quantite.quantize(Decimal('0.01')) if quantite is not None else None,
        })

    resultats.sort(key=lambda x: (x['produit'].nom if x['produit'] else (x['nom'] or '')).lower())
    return resultats
