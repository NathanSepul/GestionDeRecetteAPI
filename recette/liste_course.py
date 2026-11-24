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


def _noeud(unite):
    """
    Où se trouve une quantité dans ce produit, et le facteur vers l'unité de base de ce nœud :
    unité convertible -> sa dimension (g, ml, cm, pièce) ; mesure propre (gousse, botte...) -> l'unité elle-même.
    """
    if unite is None:
        return PIECE, Decimal(1)
    if unite.facteur is not None:
        return unite.dimension, unite.facteur
    return ('unite', unite.pk), Decimal(1)


def _convertir(quantite, unite, cible, equivalences):
    """
    Quantité exprimée dans l'unité cible, en enchaînant les équivalences du produit
    ("1 ml = 1,4 g", "1 pièce = 150 g", "1 gousse = 5 g"...) ; None si aucun chemin n'existe.
    """
    depart, facteur = _noeud(unite)
    arrivee, facteur_cible = _noeud(cible)
    montant = quantite * facteur
    if depart == arrivee:
        return montant / facteur_cible

    voisins = {}
    for equivalence in equivalences:
        a, fa = _noeud(equivalence.unite)
        b, fb = _noeud(equivalence.uniteCible)
        if a == b:
            continue
        k = (equivalence.quantiteCible * fb) / (equivalence.quantite * fa)  # 1 unité de base de a = k unités de base de b
        voisins.setdefault(a, []).append((b, k))
        voisins.setdefault(b, []).append((a, 1 / k))

    # parcours en largeur : le chemin le plus court (une équivalence directe plutôt qu'un détour)
    multiplicateurs, a_visiter = {depart: Decimal(1)}, [depart]
    while a_visiter:
        noeud = a_visiter.pop(0)
        for voisin, k in voisins.get(noeud, ()):
            if voisin not in multiplicateurs:
                multiplicateurs[voisin] = multiplicateurs[noeud] * k
                if voisin == arrivee:
                    return montant * multiplicateurs[voisin] / facteur_cible
                a_visiter.append(voisin)
    return None


def _equivalences_du_produit(produit, equivalences):
    """Équivalences internes au produit (sans produit cible)."""
    return [e for e in equivalences.get(produit.pk, ()) if not e.produitCible_id]


def _vers_produit_achete(produit, quantite, unite, equivalences):
    """
    Ce qu'on achète réellement : "4 cl de jus de citron" -> "1 citron", en remontant les produits de base grâce à
    l'équivalence du dérivé vers son produit de base ("40 ml de jus de citron = 1 citron").
    Sans équivalence applicable : 1 pour 1, dans la même unité.
    """
    vus = set()
    while produit.produitDeBase_id and produit.pk not in vus:
        vus.add(produit.pk)
        lien = next((e for e in equivalences.get(produit.pk, ()) if e.produitCible_id == produit.produitDeBase_id), None)
        if lien is not None and quantite is not None:
            quantite_lien = _convertir(quantite, unite, lien.unite, _equivalences_du_produit(produit, equivalences))
            if quantite_lien is not None:
                quantite, unite = quantite_lien / lien.quantite * lien.quantiteCible, lien.uniteCible
        produit = produit.produitDeBase
    return produit, quantite, unite


def _vers_unite_achat(produit, quantite, unite, unites_par_id, equivalences):
    """
    Exprime la quantité dans l'unité d'achat du produit : "1 cs de sucre" -> 15 g, "150 g d'oignon" -> 1 (pièce),
    "10 g d'ail" -> 2 gousses. Sans unité d'achat, une mesure propre ("2 tranches de gingembre") passe dans son unité
    de référence ; sans conversion possible, la quantité est inchangée.
    """
    propres = _equivalences_du_produit(produit, equivalences)
    cible = unites_par_id.get(produit.uniteAchat_id)
    if cible is None:
        if unite is not None and unite.facteur is None and quantite is not None:
            mesure = next((e for e in propres if e.unite_id == unite.pk), None)
            if mesure is not None:
                return quantite / mesure.quantite * mesure.quantiteCible, mesure.uniteCible
        return quantite, unite

    unite_cible = None if cible.dimension == PIECE else cible  # "pièce" : affichée sans unité ("3 oignons")
    if quantite is None:
        return None, unite_cible
    if unite == unite_cible:
        return quantite, unite
    convertie = _convertir(quantite, unite, cible, propres)
    if convertie is not None:
        return convertie, unite_cible
    return quantite, unite


def generer_liste_course(portions_par_recette):
    """
    Liste de courses de plusieurs recettes : {recette: nombre de portions voulu} -> lignes agrégées.
    Charge en une fois unités, rayons et équivalences (petites tables) pour éviter une requête par ligne.
    """
    from recette.models import Equivalence, Ingredient, Rayon, Unite

    facteurs_par_recette = {
        recette.id: (Decimal(portion) / Decimal(recette.portion)) if recette.portion else Decimal(1)
        for recette, portion in portions_par_recette.items()
    }
    unites_par_id = {unite.id: unite for unite in Unite.objects.all()}
    rayons_par_id = {rayon.id: rayon for rayon in Rayon.objects.all()}
    equivalences = {}
    for equivalence in Equivalence.objects.all():
        equivalence.unite = unites_par_id.get(equivalence.unite_id)
        equivalence.uniteCible = unites_par_id.get(equivalence.uniteCible_id)
        equivalences.setdefault(equivalence.produit_id, []).append(equivalence)

    ingredients = Ingredient.objects.filter(
        recette_id__in=facteurs_par_recette, isSection=False,
    ).select_related('produit__produitDeBase')
    for ingredient in ingredients:
        ingredient.unite = unites_par_id.get(ingredient.unite_id)

    return construire_liste_course(ingredients, facteurs_par_recette, unites_par_id, rayons_par_id, equivalences)


def construire_liste_course(ingredients, facteurs_par_recette, unites_par_id, rayons_par_id=None, equivalences=None):
    """
    Agrège les ingrédients par produit acheté (produit de base, ou nom libre), exprimés dans l'unité d'achat du produit :
    200 g + 0,5 kg de beurre -> 700 g ; 6 cs + 225 g de sucre -> 315 g ; 2 oignons + 150 g d'oignon -> 3 oignons ;
    4 cl de jus de citron -> 1 citron (ratio du produit dérivé).
    Sans unité d'achat ou sans conversion connue, chaque famille d'unités reste sur sa ligne.
    Les pièces et mesures (gousse, botte...) sont arrondies au-dessus : on n'achète pas 3,75 citrons.
    Tri : par rayon (ordre de parcours), produits sans rayon ensuite, produits "placard" en dernier.
    """
    rayons_par_id = rayons_par_id or {}
    equivalences = equivalences or {}
    groupes = {}

    for ingredient in ingredients:
        unite = ingredient.unite
        facteur_portion = facteurs_par_recette.get(ingredient.recette_id, Decimal(1))
        quantite = ingredient.quantite * facteur_portion if ingredient.quantite is not None else None
        produit = None
        if ingredient.produit_id:
            produit, quantite, unite = _vers_produit_achete(ingredient.produit, quantite, unite, equivalences)
            quantite, unite = _vers_unite_achat(produit, quantite, unite, unites_par_id, equivalences)

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
