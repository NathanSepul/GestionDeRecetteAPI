from decimal import ROUND_CEILING, Decimal

PIECE = 'piece'


def _unite_info(unite):
    """(dimension, facteur) d'une unité ; sans unité = pièce ("2 oignons")."""
    if unite is None:
        return PIECE, Decimal(1)
    return unite.dimension, unite.facteur


def _unite_affichage(unites_utilisees):
    """
    La plus petite unité utilisée dans le groupe : on part de là, puis on monte si la quantité le justifie.
    Les unités plus petites que l'unité de base (pincée ≈ 0,5 ml) ne servent que si elles sont seules :
    1 pincée + 1 cc de cannelle -> "1,1 cc", pas "11 pincées".
    """
    unites = [u for u in unites_utilisees if (_unite_info(u)[1] or 1) >= 1] or unites_utilisees
    return min(unites, key=lambda u: (_unite_info(u)[1], u is not None))


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
    """Ce qu'on achète réellement : "4 cl de jus de citron" -> "1 citron" (en remontant les produits de base)."""
    vus = set()
    while produit.produitDeBase_id and produit.pk not in vus:
        vus.add(produit.pk)
        quantite, unite = _appliquer_ratio(produit, quantite, unite, unites_par_id)
        produit = produit.produitDeBase
    return produit, quantite, unite


def _en_grammes(produit, quantite, unite):
    """Poids d'une quantité du produit, grâce à sa densité ou au poids d'une pièce ; None si on ne sait pas."""
    dimension, facteur = _unite_info(unite)
    if dimension == 'masse':
        return quantite * facteur
    if dimension == 'volume' and produit.densite:
        return quantite * facteur * produit.densite
    if dimension == PIECE and produit.poidsPiece:
        return quantite * facteur * produit.poidsPiece
    return None


def _depuis_grammes(produit, grammes, cible, mesures):
    """Exprime un poids dans l'unité cible (g, ml, pièce, gousse...) ; (None, None) si on ne sait pas."""
    dimension, facteur = _unite_info(cible)
    if dimension == 'masse':
        return grammes / facteur, cible
    if dimension == 'volume' and produit.densite:
        return grammes / produit.densite / facteur, cible
    if dimension == PIECE and produit.poidsPiece:
        return grammes / produit.poidsPiece, None
    mesure = mesures.get((produit.pk, cible.pk)) if dimension == 'vague' else None
    if mesure:
        grammes_par_mesure = _en_grammes(produit, mesure.quantite, mesure.unite_reference)
        if grammes_par_mesure:
            return grammes / grammes_par_mesure, cible
    return None, None


def _vers_unite_achat(produit, quantite, unite, unites_par_id, mesures):
    """
    Exprime la quantité dans l'unité d'achat du produit : "1 cs de sucre" -> 15 g, "150 g d'oignon" -> 1 (pièce),
    "10 g d'ail" -> 2 gousses. Sans unité d'achat, ou sans conversion possible : quantité inchangée.
    """
    # mesure propre au produit ("1 gousse d'ail = 5 g") : on passe d'abord dans son unité de référence
    mesure = mesures.get((produit.pk, unite.pk)) if unite is not None and unite.dimension == 'vague' else None
    if mesure and quantite is not None:
        quantite, unite = quantite * mesure.quantite, mesure.unite_reference

    cible = unites_par_id.get(produit.uniteAchat_id)
    if cible is None:
        return quantite, unite
    unite_cible = None if cible.dimension == PIECE else cible  # "pièce" : affichée sans unité ("3 oignons")
    if quantite is None:
        return None, unite_cible
    if unite == unite_cible:
        return quantite, unite

    dimension, facteur = _unite_info(unite)
    dimension_cible, facteur_cible = _unite_info(cible)
    if dimension == dimension_cible and facteur and facteur_cible:
        return quantite * facteur / facteur_cible, unite_cible

    grammes = _en_grammes(produit, quantite, unite)
    if grammes is not None:
        quantite_cible, unite_convertie = _depuis_grammes(produit, grammes, cible, mesures)
        if quantite_cible is not None:
            return quantite_cible, unite_convertie
    return quantite, unite


def generer_liste_course(portions_par_recette):
    """
    Liste de courses de plusieurs recettes : {recette: nombre de portions voulu} -> lignes agrégées.
    Charge en une fois unités et rayons (une dizaine chacun) pour éviter une requête par ligne.
    """
    from recette.models import Ingredient, ProduitMesure, Rayon, Unite

    facteurs_par_recette = {
        recette.id: (Decimal(portion) / Decimal(recette.portion)) if recette.portion else Decimal(1)
        for recette, portion in portions_par_recette.items()
    }
    unites_par_id = {unite.id: unite for unite in Unite.objects.all()}
    rayons_par_id = {rayon.id: rayon for rayon in Rayon.objects.all()}
    mesures = {}
    for mesure in ProduitMesure.objects.all():
        mesure.unite_reference = unites_par_id.get(mesure.uniteReference_id)
        mesures[(mesure.produit_id, mesure.unite_id)] = mesure

    ingredients = Ingredient.objects.filter(
        recette_id__in=facteurs_par_recette, isSection=False,
    ).select_related('produit__produitDeBase')
    for ingredient in ingredients:
        ingredient.unite = unites_par_id.get(ingredient.unite_id)

    return construire_liste_course(ingredients, facteurs_par_recette, unites_par_id, rayons_par_id, mesures)


def construire_liste_course(ingredients, facteurs_par_recette, unites_par_id, rayons_par_id=None, mesures=None):
    """
    Agrège les ingrédients par produit acheté (produit de base, ou nom libre), exprimés dans l'unité d'achat du produit :
    200 g + 0,5 kg de beurre -> 700 g ; 6 cs + 225 g de sucre -> 315 g ; 2 oignons + 150 g d'oignon -> 3 oignons ;
    4 cl de jus de citron -> 1 citron (ratio du produit dérivé).
    Sans unité d'achat ou sans conversion connue, chaque famille d'unités reste sur sa ligne.
    Les pièces et mesures (gousse, botte...) sont arrondies au-dessus : on n'achète pas 3,75 citrons.
    Tri : par rayon (ordre de parcours), produits sans rayon ensuite, produits "placard" en dernier.
    """
    rayons_par_id = rayons_par_id or {}
    mesures = mesures or {}
    groupes = {}

    for ingredient in ingredients:
        unite = ingredient.unite
        facteur_portion = facteurs_par_recette.get(ingredient.recette_id, Decimal(1))
        quantite = ingredient.quantite * facteur_portion if ingredient.quantite is not None else None
        produit = None
        if ingredient.produit_id:
            produit, quantite, unite = _vers_produit_achete(ingredient.produit, quantite, unite, unites_par_id)
            quantite, unite = _vers_unite_achat(produit, quantite, unite, unites_par_id, mesures)

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
            if unite is None or unite.dimension == 'vague':
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
