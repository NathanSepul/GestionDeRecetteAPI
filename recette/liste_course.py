from decimal import ROUND_CEILING, Decimal

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


def _appliquer_ratio(produit, quantite, unite, unites_par_id):
    """
    Convertit une quantité du produit en quantité de son produit de base grâce au ratio :
    "1 gousse = 1 cc" -> 1 cs d'ail haché = 3 gousses d'ail. Sans ratio applicable (pas de ratio,
    ou unité d'une autre dimension que celle du ratio) : 1 pour 1, dans la même unité.
    """
    if produit.ratioQuantite is None or quantite is None:
        return quantite, unite

    unite_ratio = unites_par_id.get(produit.ratioUnite_id)
    dimension, facteur = _unite_info(unite)
    dimension_ratio, facteur_ratio = _unite_info(unite_ratio)

    if unite == unite_ratio:
        facteur = facteur_ratio = Decimal(1)  # même unité, même non convertible (gousse, tranche...)
    elif facteur is None or facteur_ratio is None or dimension != dimension_ratio:
        return quantite, unite

    nombre_de_ratios = (quantite * facteur) / (produit.ratioQuantite * facteur_ratio)
    return nombre_de_ratios * produit.ratioQuantiteBase, unites_par_id.get(produit.ratioUniteBase_id)


def _vers_produit_achete(produit, quantite, unite, unites_par_id):
    """Ce qu'on achète réellement : "1 cs d'ail haché" -> "3 gousses d'ail" (en remontant les produits de base)."""
    vus = set()
    while produit.produitDeBase_id and produit.pk not in vus:
        vus.add(produit.pk)
        quantite, unite = _appliquer_ratio(produit, quantite, unite, unites_par_id)
        produit = produit.produitDeBase
    return produit, quantite, unite


def generer_liste_course(portions_par_recette):
    """
    Liste de courses de plusieurs recettes : {recette: nombre de portions voulu} -> lignes agrégées.
    Charge en une fois unités et rayons (une dizaine chacun) pour éviter une requête par ligne.
    """
    from recette.models import Ingredient, Rayon, Unite

    facteurs_par_recette = {
        recette.id: (Decimal(portion) / Decimal(recette.portion)) if recette.portion else Decimal(1)
        for recette, portion in portions_par_recette.items()
    }
    unites_par_id = {unite.id: unite for unite in Unite.objects.all()}
    rayons_par_id = {rayon.id: rayon for rayon in Rayon.objects.all()}

    ingredients = Ingredient.objects.filter(
        recette_id__in=facteurs_par_recette, isSection=False,
    ).select_related('produit__produitDeBase')
    for ingredient in ingredients:
        ingredient.unite = unites_par_id.get(ingredient.unite_id)

    return construire_liste_course(ingredients, facteurs_par_recette, unites_par_id, rayons_par_id)


def construire_liste_course(ingredients, facteurs_par_recette, unites_par_id, rayons_par_id=None):
    """
    Agrège les ingrédients par produit acheté (produit de base, ou nom libre) et par dimension d'unité :
    200 g + 0,5 kg de beurre -> 700 g ; 1 cs + 1 cc d'huile -> 20 ml ;
    1 cs d'ail haché + 2 gousses d'ail -> 5 gousses d'ail (ratio du produit dérivé).
    Les unités non convertibles (pincée...) ne s'additionnent qu'entre elles.
    Un même produit dans deux dimensions (2 oignons + 150 g d'oignon) reste sur deux lignes.
    Les quantités sans unité (pièces) sont arrondies à l'unité supérieure : on n'achète pas 3,75 citrons.
    Tri : par rayon (ordre de parcours), produits sans rayon ensuite, produits "placard" en dernier.
    """
    rayons_par_id = rayons_par_id or {}
    groupes = {}

    for ingredient in ingredients:
        unite = ingredient.unite
        facteur_portion = facteurs_par_recette.get(ingredient.recette_id, Decimal(1))
        quantite = ingredient.quantite * facteur_portion if ingredient.quantite is not None else None
        produit = None
        if ingredient.produit_id:
            produit, quantite, unite = _vers_produit_achete(ingredient.produit, quantite, unite, unites_par_id)

        dimension, facteur = _unite_info(unite)
        convertible = facteur is not None

        if produit:
            cle_produit = ('produit', produit.pk)
        else:
            cle_produit = ('nom', (ingredient.nom or '').strip().lower())
        cle_unite = dimension if convertible else ('unite', unite.id)

        groupe = groupes.setdefault((cle_produit, cle_unite), {
            'produit': produit,
            'nom': ingredient.nom if not produit else None,
            'unites': [],
            'derives': {},  # nom du produit dérivé ("jaune d'œuf") -> quantité, en unité de base
            'quantite_base': None,  # en unité de base (g, ml, pièce, cm) ou dans l'unité elle-même si non convertible
        })
        if unite not in groupe['unites']:
            groupe['unites'].append(unite)

        if quantite is not None and convertible:
            quantite = quantite * facteur

        if produit and ingredient.produit_id != produit.pk:
            derive = groupe['derives'].setdefault(ingredient.produit.nom, None)
            if quantite is not None:
                groupe['derives'][ingredient.produit.nom] = quantite if derive is None else derive + quantite
        elif quantite is not None:
            groupe['quantite_base'] = quantite if groupe['quantite_base'] is None else groupe['quantite_base'] + quantite

    # Dérivés différents d'un même produit = souvent les mêmes unités séparées (5 jaunes + 5 blancs = 5 œufs) :
    # on ajoute le plus grand, pas la somme
    for groupe in groupes.values():
        quantites_derives = [q for q in groupe['derives'].values() if q is not None]
        if quantites_derives:
            groupe['quantite_base'] = (groupe['quantite_base'] or 0) + max(quantites_derives)

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

        if quantite is not None:
            quantite = quantite.quantize(Decimal('0.01'))
            if unite is None:
                quantite = quantite.quantize(Decimal('1'), rounding=ROUND_CEILING)

        produit = groupe['produit']
        resultats.append({
            'produit': produit,
            'nom': groupe['nom'],
            'precision': ', '.join(sorted(groupe['derives'])) or None,
            'unite': unite,
            'quantite': quantite,
            'rayon': rayons_par_id.get(produit.rayon_id) if produit else None,
            'placard': produit.placard if produit else False,
        })

    resultats.sort(key=lambda x: (
        x['placard'],
        x['rayon'].noOrdre if x['rayon'] else float('inf'),
        (x['produit'].nom if x['produit'] else (x['nom'] or '')).lower(),
    ))
    return resultats
