"""
Import d'une recette depuis une vidéo (TikTok).

Une vidéo ne publie pas de recette structurée (JSON-LD) comme Marmiton. On lit sa description avec yt-dlp, puis :
1. si elle contient visiblement la recette : l'API Claude la met en forme à partir de la description seule (~5 s) ;
2. sinon, ou si la recette obtenue est incomplète : la vidéo est téléchargée, voix transcrite par Whisper et images
   (texte affiché à l'écran), voir import_media.py ; Claude en fait la recette avec la description (import_ia.py).
Les lignes d'ingrédients passent ensuite par le même analyseur que l'import web (quantité, unité, produit).

Le traitement a lieu en arrière-plan (lancer_import) : de quelques secondes à deux minutes environ.
"""
import logging
import re
import threading
from datetime import timedelta
from urllib.parse import urlparse

from django.db import close_old_connections, connection, transaction
from django.utils import timezone

from recette.import_ia import ClaudeIndisponible, ia_configuree, ia_disponible, structurer_avec_claude
from recette.import_media import analyser_video, media_disponible
from recette.import_web import PORTION_PAR_DEFAUT, ImportRecetteErreur, _adresse_publique, _texte, creer_recette_importee
from recette.models import DUREE_MAX_MINUTES, ImportVideo

logger = logging.getLogger(__name__)

# Domaines lus avec yt-dlp (sous-domaines compris : www., vm., m.)
DOMAINES_VIDEO = {'tiktok.com': 'TikTok'}
TAILLE_MAX_DESCRIPTION = 5000
# Un import resté "en cours" plus longtemps a été interrompu (serveur redémarré pendant le traitement)
DUREE_MAX_IMPORT = timedelta(minutes=30)


def _site_video(host):
    host = (host or '').lower().rstrip('.')
    return next((nom for domaine, nom in DOMAINES_VIDEO.items() if host == domaine or host.endswith('.' + domaine)), None)


def est_url_video(url):
    return _site_video(urlparse(url).hostname) is not None


def import_video_actif():
    """yt-dlp installé et API Claude configurée."""
    if not ia_configuree():
        return False
    try:
        import yt_dlp  # noqa: F401
    except ImportError:
        return False
    return True


def sites_video():
    """Pour la liste des sites affichée à l'import."""
    if not import_video_actif():
        return []
    return [{'nom': nom, 'domaine': domaine, 'url': f'https://www.{domaine}'} for domaine, nom in DOMAINES_VIDEO.items()]


def verifier_url_video(url):
    parsed = urlparse(url)
    if parsed.scheme not in ('http', 'https') or not _site_video(parsed.hostname) or not _adresse_publique(parsed.hostname):
        raise ImportRecetteErreur("Adresse invalide.")
    if not import_video_actif():
        raise ImportRecetteErreur("L'import depuis une vidéo n'est pas activé sur ce serveur.")


# ---------- Lecture de la vidéo ----------

def lire_video(url):
    """{'titre', 'description', 'miniature'} de la vidéo, sans la télécharger."""
    import yt_dlp

    options = {'quiet': True, 'no_warnings': True, 'skip_download': True, 'noplaylist': True, 'socket_timeout': 15}
    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as e:
        logger.info("Import vidéo : lecture impossible de %s (%s)", url, e)
        raise ImportRecetteErreur("Impossible de lire cette vidéo (lien privé, supprimé, ou site modifié : réessaie plus tard).")

    # Un lien court (vm.tiktok.com) est résolu par yt-dlp : on vérifie qu'il mène bien à une vidéo du site
    if not est_url_video(info.get('webpage_url') or url):
        raise ImportRecetteErreur("Adresse invalide.")
    return {
        'titre': (info.get('title') or '').strip(),
        'description': (info.get('description') or '').strip()[:TAILLE_MAX_DESCRIPTION],
        'miniature': info.get('thumbnail'),
    }


# ---------- Mise en forme par l'IA ----------

def _entier(valeur, minimum, maximum):
    return valeur if isinstance(valeur, int) and not isinstance(valeur, bool) and minimum <= valeur <= maximum else None


def _lignes(valeurs, longueur_max):
    return [(False, t[:longueur_max]) for t in (_texte(v) for v in (valeurs if isinstance(valeurs, list) else [])) if t]


def donnees_recette(video, recette_ia):
    """Réponse de l'IA au format de creer_recette_importee."""
    titre = _texte(recette_ia.get('titre')) or _texte(video['titre']) or 'Recette importée'
    return {
        'titre': titre[:100],
        'portion': _entier(recette_ia.get('portion'), 1, 100) or PORTION_PAR_DEFAUT,
        'image': video['miniature'],
        'tempsPreparation': _entier(recette_ia.get('tempsPreparation'), 1, DUREE_MAX_MINUTES),
        'tempsCuisson': _entier(recette_ia.get('tempsCuisson'), 1, DUREE_MAX_MINUTES),
        'tempsRepos': None,
        'ingredients': _lignes(recette_ia.get('ingredients'), 500),
        'etapes': _lignes(recette_ia.get('etapes'), 2000),
    }


RE_QUANTITE_TEXTE = re.compile(r'\d+\s*(?:g|kg|ml|cl|l|c\.|cas|cac|cs|cc|cuill|gousses?|tranches?|pincées?)\b', re.I)
RE_SECTION_INGREDIENTS = re.compile(r"ingr[ée]dients?\s*:|il\s+(?:te|vous)\s+faut\s*:", re.I)


def description_avec_recette(description):
    """
    La description contient-elle visiblement une recette (titre "Ingrédients :" ou plusieurs quantités) ?
    Sert seulement à éviter de télécharger la vidéo : c'est Claude qui lit la description dans tous les cas.
    """
    if len(description) < 100:
        return False
    return bool(RE_SECTION_INGREDIENTS.search(description) or len(RE_QUANTITE_TEXTE.findall(description)) >= 3)


def recette_complete(donnees):
    return sum(1 for est_section, _ in donnees['ingredients'] if not est_section) >= 2 and any(not s for s, _ in donnees['etapes'])


def importer_recette_depuis_video(url, user, type_recette, importer_image=True, tache=None):
    if not ia_disponible():
        if not ia_configuree():
            raise ImportRecetteErreur("L'import depuis une vidéo n'est pas activé sur ce serveur.")
        raise ImportRecetteErreur("La lecture automatique des recettes vidéo est momentanément indisponible. Réessaie plus tard.")

    video = lire_video(url)
    donnees = None
    try:
        # 1. Recette visiblement écrite dans la description : Claude la lit seule, sans télécharger la vidéo
        if description_avec_recette(video['description']):
            donnees = donnees_recette(video, structurer_avec_claude(video['titre'], video['description'], tache=tache))
            if not recette_complete(donnees):
                donnees = None
        # 2. Sinon : voix et texte à l'écran, lus par Claude avec la description
        if donnees is None:
            transcription, images = analyser_video(url) if media_disponible() else ('', [])
            donnees = donnees_recette(video, structurer_avec_claude(video['titre'], video['description'], transcription, images, tache=tache))
    except ClaudeIndisponible:
        raise ImportRecetteErreur("La lecture automatique des recettes vidéo est momentanément indisponible. Réessaie plus tard.")

    if not donnees['ingredients'] and not donnees['etapes']:
        raise ImportRecetteErreur("Aucune recette trouvée dans cette vidéo.")
    return creer_recette_importee(donnees, url, user, type_recette, importer_image)


# ---------- Arrière-plan ----------

# Une vidéo à la fois par processus : la transcription occupe déjà tout le processeur
_un_import_a_la_fois = threading.Lock()


def traiter(import_id):
    """Traite un import en attente (appelé dans le fil d'arrière-plan ; directement dans les tests)."""
    with _un_import_a_la_fois:
        tache = ImportVideo.objects.select_related('user', 'typeRecette').get(pk=import_id)
        if tache.statut != ImportVideo.Statut.ATTENTE:
            return
        tache.statut = ImportVideo.Statut.EN_COURS
        tache.save(update_fields=['statut', 'majLe'])
        try:
            tache.recette = importer_recette_depuis_video(tache.url, tache.user, tache.typeRecette, tache.importerImage, tache=tache)
            tache.statut = ImportVideo.Statut.TERMINE
        except ImportRecetteErreur as e:
            tache.statut, tache.erreur = ImportVideo.Statut.ERREUR, str(e)
        except Exception:
            logger.exception("Import vidéo %s : erreur inattendue", import_id)
            tache.statut, tache.erreur = ImportVideo.Statut.ERREUR, "Erreur inattendue pendant l'import."
        tache.save(update_fields=['statut', 'recette', 'erreur', 'majLe'])


def _fil(import_id):
    close_old_connections()
    try:
        traiter(import_id)
    finally:
        connection.close()


def lancer_import(tache):
    """Démarre le traitement après le commit (la tâche doit être visible du fil d'arrière-plan)."""
    transaction.on_commit(lambda: threading.Thread(target=_fil, args=(tache.id,), daemon=True, name=f"import-video-{tache.id}").start())


def statut_affiche(tache):
    """Statut pour le client : un import bloqué (serveur redémarré pendant le traitement) est signalé en erreur."""
    en_cours = tache.statut in (ImportVideo.Statut.ATTENTE, ImportVideo.Statut.EN_COURS)
    if en_cours and timezone.now() - tache.creeLe > DUREE_MAX_IMPORT:
        return ImportVideo.Statut.ERREUR, "L'import a été interrompu. Réessaie."
    return tache.statut, tache.erreur
