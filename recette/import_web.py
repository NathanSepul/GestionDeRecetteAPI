"""
Import d'une recette depuis un site de cuisine (Marmiton, 750g...).

Les sites de recettes publient, pour Google, un bloc JSON-LD schema.org "Recipe" : titre, portions, photo,
ingrédients et étapes y sont déjà séparés. On le lit plutôt que la mise en page HTML, qui change souvent.

Les ingrédients arrivent en texte libre ("200 g de farine") : on en déduit quantité, unité et produit.
Un produit introuvable (ou trouvé seulement en partie) garde le texte d'origine dans `nom`,
pour que l'utilisateur choisisse le bon produit en relisant la recette.

Sécurité : seules les pages des sites actifs de SiteImport (admin) sont téléchargées (redirections comprises),
sinon n'importe qui pourrait faire appeler au serveur une adresse interne (SSRF).
"""
import html
import ipaddress
import json
import logging
import re
import socket
import unicodedata
import urllib.request
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from io import BytesIO
from urllib.parse import urlparse

from django.core.files.base import ContentFile
from django.db import transaction
from PIL import Image

from recette.models import DUREE_MAX_MINUTES, Ingredient, Preparation, Produit, Recette, SiteImport, Unite

logger = logging.getLogger(__name__)

def sites_import():
    """Sites acceptés à l'import (gérés dans l'admin : modèle SiteImport), aussi listés dans l'interface."""
    return SiteImport.objects.filter(actif=True)

USER_AGENT = 'Mozilla/5.0 (compatible; GestionDeRecette/1.0; import de recette personnelle)'
TIMEOUT_S = 10
TAILLE_MAX_PAGE = 3 * 1024 * 1024
TAILLE_MAX_IMAGE = 8 * 1024 * 1024
PORTION_PAR_DEFAUT = 4
EXTENSIONS_IMAGE = {'image/jpeg': 'jpg', 'image/png': 'png', 'image/webp': 'webp'}


class ImportRecetteErreur(Exception):
    """Erreur à montrer telle quelle à l'utilisateur."""


# ---------- Téléchargement ----------

def _domaine_autorise(host):
    host = (host or '').lower().rstrip('.')
    return any(host == d or host.endswith('.' + d) for d in sites_import().values_list('domaine', flat=True))


def _adresse_publique(host):
    """Refuse localhost, réseau local, métadonnées cloud... (toutes les adresses résolues doivent être publiques)."""
    try:
        adresses = {info[4][0] for info in socket.getaddrinfo(host, None)}
    except socket.gaierror:
        return False
    return bool(adresses) and all(ipaddress.ip_address(a).is_global for a in adresses)


def _verifier_url(url, domaines_requis):
    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https') or not parsed.hostname:
        raise ImportRecetteErreur("Adresse invalide.")
    if parsed.port not in (None, 80, 443):
        raise ImportRecetteErreur("Adresse invalide.")
    if domaines_requis and not _domaine_autorise(parsed.hostname):
        raise ImportRecetteErreur(
            "Ce site n'est pas pris en charge. Sites acceptés : " + ", ".join(sites_import().values_list('nom', flat=True)) + "."
        )
    if not _adresse_publique(parsed.hostname):
        raise ImportRecetteErreur("Adresse invalide.")


class _RedirectionVerifiee(urllib.request.HTTPRedirectHandler):
    """Chaque redirection est revérifiée : un site autorisé ne doit pas pouvoir renvoyer vers une adresse interne."""

    def __init__(self, domaines_requis):
        self.domaines_requis = domaines_requis

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _verifier_url(newurl, self.domaines_requis)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _telecharger(url, taille_max, domaines_requis):
    """Renvoie (contenu, content-type, charset)."""
    _verifier_url(url, domaines_requis)
    opener = urllib.request.build_opener(_RedirectionVerifiee(domaines_requis))
    requete = urllib.request.Request(url, headers={'User-Agent': USER_AGENT, 'Accept-Language': 'fr'})
    try:
        with opener.open(requete, timeout=TIMEOUT_S) as reponse:
            contenu = reponse.read(taille_max + 1)
            if len(contenu) > taille_max:
                raise ImportRecetteErreur("La page est trop volumineuse.")
            return contenu, reponse.headers.get_content_type(), reponse.headers.get_content_charset()
    except ImportRecetteErreur:
        raise
    except Exception as e:
        logger.info("Import recette : échec du téléchargement de %s (%s)", url, e)
        raise ImportRecetteErreur("Impossible de lire cette page. Vérifie le lien ou réessaie plus tard.")


# ---------- Lecture du JSON-LD ----------

def _texte(valeur):
    """Texte propre : sans balises HTML, entités décodées, espaces normalisés."""
    if not isinstance(valeur, str):
        return ''
    valeur = html.unescape(re.sub(r'<[^>]+>', ' ', valeur))
    return re.sub(r'\s+', ' ', valeur).strip()


def _est_recette(objet):
    if not isinstance(objet, dict):
        return False
    types = objet.get('@type')
    return 'Recipe' in (types if isinstance(types, list) else [types])


def _chercher_recette(donnees):
    """Le bloc Recipe peut être seul, dans une liste ou dans un @graph."""
    if _est_recette(donnees):
        return donnees
    if isinstance(donnees, list):
        candidats = donnees
    elif isinstance(donnees, dict):
        candidats = donnees.get('@graph') or []
    else:
        candidats = []
    for candidat in candidats:
        trouve = _chercher_recette(candidat)
        if trouve:
            return trouve
    return None


def _portion(rendement):
    if isinstance(rendement, list):
        rendement = rendement[0] if rendement else None
    if isinstance(rendement, (int, float)):
        nombre = int(rendement)
    else:
        trouve = re.search(r'\d+', str(rendement or ''))
        nombre = int(trouve.group()) if trouve else PORTION_PAR_DEFAUT
    return min(max(nombre, 1), 100)


def _url_image(image):
    if isinstance(image, list):
        image = image[0] if image else None
    if isinstance(image, dict):
        image = image.get('url') or image.get('contentUrl')
    return image if isinstance(image, str) else None


def _etapes(instructions):
    """Liste de (isSection, texte) ; accepte texte brut, liste de textes, HowToStep et HowToSection."""
    if isinstance(instructions, str):
        return [(False, t) for t in (_texte(l) for l in re.split(r'\n+|<br\s*/?>', instructions)) if t]

    etapes = []
    for element in instructions or []:
        if isinstance(element, str):
            texte = _texte(element)
            if texte:
                etapes.append((False, texte))
        elif isinstance(element, dict):
            if 'itemListElement' in element:
                nom = _texte(element.get('name'))
                if nom:
                    etapes.append((True, nom))
                etapes.extend(_etapes(element['itemListElement']))
            else:
                texte = _texte(element.get('text') or element.get('name'))
                if texte:
                    etapes.append((False, texte))
    return etapes


RE_DUREE_ISO = re.compile(r'^P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:\d+(?:\.\d+)?S)?)?$', re.I)


def _minutes(duree):
    """Durée ISO 8601 ('PT1H30M', 'P0DT0H15M') -> 90 / 15 ; None si absente, nulle ou illisible."""
    trouve = RE_DUREE_ISO.match(duree.strip()) if isinstance(duree, str) else None
    if not trouve:
        return None
    jours, heures, minutes = (int(v or 0) for v in trouve.groups())
    total = jours * 24 * 60 + heures * 60 + minutes
    return total if 0 < total <= DUREE_MAX_MINUTES else None


def _durees(recette):
    """(préparation, cuisson, repos) en minutes. Le repos n'existe pas dans schema.org : c'est ce que totalTime
    a en plus de préparation + cuisson (temps de repos, de levée, de réfrigération...)."""
    preparation, cuisson = _minutes(recette.get('prepTime')), _minutes(recette.get('cookTime'))
    total = _minutes(recette.get('totalTime'))
    repos = total - (preparation or 0) - (cuisson or 0) if total and (preparation or cuisson) else None
    return preparation, cuisson, (repos if repos and repos > 0 else None)


class _GroupesWprm(HTMLParser):
    """Groupes d'ingrédients de WP Recipe Maker (extension WordPress utilisée par beaucoup de blogs).
    Son JSON-LD donne les ingrédients à plat ; le HTML les range en groupes ("Sauce", "Marinade"...).
    Résultat : [[nom ou '', nombre d'ingrédients], ...] dans l'ordre de la page."""

    def __init__(self):
        super().__init__()
        self.groupes = []
        self._nom = None  # morceaux du nom de groupe en cours de lecture
        self._balise_nom = None

    def handle_starttag(self, tag, attrs):
        classes = (dict(attrs).get('class') or '').split()
        if 'wprm-recipe-ingredient-group' in classes:
            self.groupes.append(['', 0])
        elif not self.groupes:
            return
        elif 'wprm-recipe-ingredient-group-name' in classes:
            self._nom, self._balise_nom = [], tag
        elif tag == 'li' and 'wprm-recipe-ingredient' in classes:
            self.groupes[-1][1] += 1

    def handle_data(self, data):
        if self._nom is not None:
            self._nom.append(data)

    def handle_endtag(self, tag):
        if self._nom is not None and tag == self._balise_nom:
            self.groupes[-1][0] = _texte(''.join(self._nom))
            self._nom = None


def _ingredients(lignes, page_html):
    """Liste de (isSection, texte) : les ingrédients du JSON-LD, avec les titres des groupes WP Recipe Maker
    s'ils correspondent exactement (même nombre d'ingrédients), sinon à plat."""
    a_plat = [(False, ligne) for ligne in lignes]
    if 'wprm-recipe-ingredient-group' not in page_html:
        return a_plat

    parseur = _GroupesWprm()
    try:
        parseur.feed(page_html)
    except Exception:
        return a_plat
    groupes = parseur.groupes
    # Fiche affichée deux fois, ingrédient vide écarté du JSON-LD... : dans le doute, pas de sections
    if not any(nom for nom, _ in groupes) or sum(n for _, n in groupes) != len(lignes):
        return a_plat

    resultat, debut = [], 0
    for nom, nombre in groupes:
        if nom:
            resultat.append((True, nom[:500]))
        resultat.extend((False, ligne) for ligne in lignes[debut:debut + nombre])
        debut += nombre
    return resultat


def extraire_recette(page_html):
    """Données utiles du bloc schema.org Recipe de la page, ou erreur si la page n'en a pas."""
    for bloc in re.findall(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', page_html, re.S | re.I):
        try:
            donnees = json.loads(bloc.strip(), strict=False)
        except ValueError:
            continue
        recette = _chercher_recette(donnees)
        if recette:
            preparation, cuisson, repos = _durees(recette)
            return {
                'tempsPreparation': preparation,
                'tempsCuisson': cuisson,
                'tempsRepos': repos,
                'titre': _texte(recette.get('name'))[:100] or 'Recette importée',
                'portion': _portion(recette.get('recipeYield')),
                'image': _url_image(recette.get('image')),
                'ingredients': _ingredients([t for t in (_texte(i) for i in recette.get('recipeIngredient') or []) if t], page_html),
                'etapes': _etapes(recette.get('recipeInstructions')),
            }
    raise ImportRecetteErreur("Aucune recette trouvée sur cette page (est-ce bien la page d'une recette ?).")


# ---------- Analyse des ingrédients ----------

def normaliser(texte):
    """'Cuillères à soupe d’Œufs' -> "cuilleres a soupe d'oeufs" (comparaisons sans accents ni majuscules)."""
    texte = (texte or '').lower().replace('œ', 'oe').replace('æ', 'ae').replace('’', "'")
    texte = ''.join(c for c in unicodedata.normalize('NFD', texte) if unicodedata.category(c) != 'Mn')
    return re.sub(r'\s+', ' ', texte).strip()


# Façons courantes d'écrire une même unité : rapprochées des unités en base via leur code, pluriel ou description
SYNONYMES_UNITES = [
    ['g', 'gr', 'gramme', 'grammes'],
    ['kg', 'kilo', 'kilos', 'kilogramme', 'kilogrammes'],
    ['l', 'litre', 'litres'],
    ['dl', 'decilitre', 'decilitres'],
    ['cl', 'centilitre', 'centilitres'],
    ['ml', 'millilitre', 'millilitres'],
    ['cs', 'c.s.', 'c.s', 'cas', 'c.a.s', 'c.a.s.', 'c. a s.', 'c. a soupe', 'cuillere a soupe', 'cuilleres a soupe'],
    ['cc', 'c.c.', 'c.c', 'cac', 'c.a.c', 'c.a.c.', 'c. a c.', 'c. a cafe', 'cuillere a cafe', 'cuilleres a cafe'],
    ['pincee', 'pincees'],
    ['verre', 'verres'],
    ['gousse', 'gousses'],
    ['tranche', 'tranches'],
    ['sachet', 'sachets'],
    ['boite', 'boites'],
    ['botte', 'bottes'],
    ['brin', 'brins'],
    ['feuille', 'feuilles'],
    ['morceau', 'morceaux'],
    ['bouquet', 'bouquets'],
    ['poignee', 'poignees'],
    ['tasse', 'tasses'],
    ['pot', 'pots'],
]

FRACTIONS = {'½': ' 1/2', '¼': ' 1/4', '¾': ' 3/4', '⅓': ' 1/3', '⅔': ' 2/3'}
# "1", "1,5", "0.5", "1 1/2", "1/2", suivi éventuellement d'une fourchette "2-3" / "2 à 3" (on garde la première valeur)
RE_QUANTITE = re.compile(r'^(\d+\s+\d+/\d+|\d+/\d+|\d+(?:[.,]\d+)?)(?:\s*(?:-|a)\s*\d+(?:[.,]\d+)?)?\s*')
RE_ARTICLE = re.compile(r"^(?:de la |de l'|des |du |de |d')")
# note finale entre parenthèses, parenthèses imbriquées comprises : "oignons verts (hachées (vraiment fin))"
RE_NOTE = re.compile(r"\s*\((.*)\)$")
# préparation en fin de ligne (texte normalisé) : "oignons emincés" -> produit "oignon" + préparation "émincés"
RE_PREPARATION = re.compile(
    r"(?:,\s*|\s)((?:hache|emince|rape|cisele|pele|presse|epluche|trempe|ramolli|fondu|coupe)(?:e|s|es)?"
    r"(?: finement| en des| en rondelles| en lamelles| en morceaux)?|mous?|molles?|en des|en rondelles|en lamelles)$"
)


def _quantite(texte):
    """Renvoie (Decimal ou None, reste du texte)."""
    for symbole, fraction in FRACTIONS.items():
        texte = texte.replace(symbole, fraction)
    texte = texte.strip()
    trouve = RE_QUANTITE.match(texte)
    if not trouve:
        return None, texte
    total = Decimal(0)
    try:
        for morceau in trouve.group(1).replace(',', '.').split():
            if '/' in morceau:
                numerateur, denominateur = morceau.split('/')
                total += Decimal(numerateur) / Decimal(denominateur)
            else:
                total += Decimal(morceau)
    except (InvalidOperation, ZeroDivisionError):
        return None, texte
    return total.quantize(Decimal('0.01')), texte[trouve.end():]


class AnalyseurIngredients:
    """Charge une fois unités et produits, puis analyse chaque ligne d'ingrédient."""

    def __init__(self):
        self.unites = {}  # alias normalisé -> Unite
        # "pièce" ne sert que d'unité d'achat : sur un ingrédient, "sans unité" veut déjà dire pièces
        for unite in Unite.objects.exclude(code='pièce'):
            alias = {normaliser(v) for v in (unite.code, unite.pluriel, unite.description) if v}
            for groupe in SYNONYMES_UNITES:
                if alias & set(groupe):
                    alias |= set(groupe)
            for a in alias:
                self.unites.setdefault(a, unite)
        # les plus longs d'abord : "cuillere a soupe" avant "c"
        self.alias_unites = sorted(self.unites, key=len, reverse=True)

        self.produits = {}  # nom ou pluriel normalisé -> Produit
        for produit in Produit.objects.only('id', 'nom', 'nomPluriel'):
            for nom in (produit.nom, produit.nomPluriel):
                if nom:
                    self.produits.setdefault(normaliser(nom), produit)

    def _unite(self, texte):
        for alias in self.alias_unites:
            if texte == alias or texte.startswith(alias + ' ') or texte.startswith(alias + "'"):
                return self.unites[alias], texte[len(alias):].strip()
        return None, texte

    def _produit(self, texte):
        """Produit dont le nom (ou le pluriel) correspond exactement, sinon None.
        Pas de correspondance partielle : "lait de coco" rangé sous "lait" fausserait la liste de courses."""
        texte = texte.strip(" .'")
        if texte in self.produits:
            return self.produits[texte]
        # pluriel simple non renseigné en base : "carottes" -> "carotte"
        if texte and texte[-1] in 'sx' and texte[:-1] in self.produits:
            return self.produits[texte[:-1]]
        return None

    def analyser(self, ligne):
        """'200 g de farine'  -> (Decimal('200.00'), <Unite g>, <Produit farine>, None, '')
        '2 oignons émincés'   -> (Decimal('2.00'), None, <Produit oignon>, None, 'émincés')
        '1 l de lait de coco' -> (Decimal('1.00'), <Unite l>, None, 'lait de coco', '')
        Sans produit reconnu, le nom (tel qu'écrit sur le site) est gardé : l'utilisateur l'associera en relisant."""
        quantite, reste = _quantite(normaliser(ligne))
        unite = None
        if quantite is not None:
            unite, reste = self._unite(reste)

        # même fin de ligne dans le texte d'origine (accents, majuscules) : la normalisation ne change pas les mots
        nb_mots = len(reste.split())
        nom = ' '.join(ligne.split()[-nb_mots:]) if nb_mots else ''
        nom = RE_ARTICLE.sub('', nom, count=1) if RE_ARTICLE.match(normaliser(nom)) else nom

        texte_produit = RE_ARTICLE.sub('', reste).strip()

        # "4 gousses d'ail (émincées)" : la note finale entre parenthèses (WP Recipe Maker...) gêne la recherche
        # du produit. Retirée pour chercher, puis gardée comme préparation, sauf si elle est trop longue
        note = RE_NOTE.search(texte_produit)
        note_origine = RE_NOTE.search(ligne.strip()) if note else None
        if note and note_origine:
            produit, preparation = self._produit_preparation(texte_produit[:note.start()].rstrip(' ,'), ligne.strip()[:note_origine.start()])
            preparation = ', '.join(p for p in (preparation, note_origine.group(1).strip(' ,')) if p)
            # sans produit, la ligne entière (note comprise) reste dans nom
            if not produit or len(preparation) > 50:
                produit, preparation = None, ''
        else:
            produit, preparation = self._produit_preparation(texte_produit, ligne)
        return quantite, unite, produit, (None if produit else (nom or ligne)[:500]), preparation

    def _produit_preparation(self, texte_produit, ligne):
        """(Produit ou None, préparation) ; texte_produit est normalisé, ligne est le texte d'origine qui se termine pareil."""
        produit = self._produit(texte_produit)
        if produit:
            return produit, ''
        # "oignons émincés", "beurre, fondu" : le produit sans sa préparation
        trouve = RE_PREPARATION.search(texte_produit)
        produit = self._produit(texte_produit[:trouve.start()].rstrip(' ,')) if trouve else None
        if not produit:
            return None, ''
        nb_mots_preparation = len(trouve.group(1).split())
        return produit, ' '.join(ligne.split()[-nb_mots_preparation:]).strip(' ,')[:50]


# ---------- Création ----------

def _telecharger_image(url):
    """Contenu de l'image (vérifié par Pillow) ou None : une photo manquante ne bloque pas l'import."""
    if not url:
        return None
    try:
        contenu, content_type, _ = _telecharger(url, TAILLE_MAX_IMAGE, domaines_requis=False)
        extension = EXTENSIONS_IMAGE.get(content_type)
        if not extension:
            return None
        with Image.open(BytesIO(contenu)) as img:
            img.verify()
        return contenu, extension
    except Exception as e:
        logger.info("Import recette : photo ignorée (%s)", e)
        return None


def titre_libre(titre, type_recette):
    """Un titre est unique par type de recette : "Crêpes" -> "Crêpes (2)" s'il existe déjà."""
    candidat, n = titre, 2
    while Recette.objects.filter(typeRecette=type_recette, titre=candidat).exists():
        suffixe = f" ({n})"
        candidat = titre[:100 - len(suffixe)] + suffixe
        n += 1
    return candidat


def importer_recette_depuis_url(url, user, type_recette, importer_image=True):
    contenu, _, charset = _telecharger(url, TAILLE_MAX_PAGE, domaines_requis=True)
    donnees = extraire_recette(contenu.decode(charset or 'utf-8', errors='replace'))
    if not donnees['ingredients'] and not donnees['etapes']:
        raise ImportRecetteErreur("La recette de cette page est vide.")

    # téléchargée avant la transaction : pas de verrou en base pendant l'attente réseau
    image = _telecharger_image(donnees['image']) if importer_image else None
    analyseur = AnalyseurIngredients()

    with transaction.atomic():
        recette = Recette.objects.create(
            user=user,
            titre=titre_libre(donnees['titre'], type_recette),
            portion=donnees['portion'],
            typeRecette=type_recette,
            source=url[:500],
            tempsPreparation=donnees['tempsPreparation'],
            tempsCuisson=donnees['tempsCuisson'],
            tempsRepos=donnees['tempsRepos'],
        )
        if image:
            contenu_image, extension = image
            recette.image.save(f"import.{extension}", ContentFile(contenu_image), save=True)

        ingredients = []
        for i, (is_section, ligne) in enumerate(donnees['ingredients']):
            if is_section:
                ingredients.append(Ingredient(recette=recette, noOrdre=i, isSection=True, nom=ligne))
                continue
            quantite, unite, produit, nom, preparation = analyseur.analyser(ligne)
            ingredients.append(Ingredient(
                recette=recette, noOrdre=i, isSection=False,
                quantite=quantite, unite=unite, produit=produit, nom=nom, preparation=preparation,
            ))
        Ingredient.objects.bulk_create(ingredients)

        Preparation.objects.bulk_create([
            Preparation(recette=recette, noOrdre=i, isSection=is_section, description=texte)
            for i, (is_section, texte) in enumerate(donnees['etapes'])
        ])

    return recette
