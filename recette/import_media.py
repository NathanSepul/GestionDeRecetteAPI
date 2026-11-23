"""
Analyse du contenu d'une vidéo, quand sa description ne contient pas la recette (voir import_video.py) :
- la voix, transcrite sur le serveur par Whisper (faster-whisper, gratuit, ~40 s de calcul par minute de vidéo) ;
- le texte affiché à l'écran (quantités souvent incrustées), via une image toutes les 2 secondes, lue ensuite par Claude.

La vidéo est téléchargée dans un dossier temporaire, supprimé à la fin.

Réglages (.env) : WHISPER_MODELE (tiny, base, small... : plus gros = plus juste et plus lent), WHISPER_LANGUE
(vide par défaut = détection automatique), VIDEO_DUREE_MAX (secondes).
Le modèle Whisper (~500 Mo pour small) est téléchargé au premier usage, puis gardé en mémoire.
"""
import io
import logging
import os
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor

from django.conf import settings

from recette.import_web import ImportRecetteErreur

logger = logging.getLogger(__name__)

INTERVALLE_IMAGES_S = 2.0
# Au-delà, les images sont espacées davantage (coût de l'analyse par Claude)
NB_MAX_IMAGES = 40
TAILLE_IMAGE = 768
TAILLE_MAX_VIDEO = 150 * 1024 * 1024
# La transcription est coupée au-delà (elle part ensuite dans la requête à Claude)
TAILLE_MAX_TRANSCRIPTION = 15000


def media_disponible():
    try:
        import av  # noqa: F401
        import faster_whisper  # noqa: F401
    except ImportError:
        return False
    return True


def telecharger_video(url, dossier):
    """Chemin du fichier vidéo téléchargé (mp4, 720 px de large au plus)."""
    import yt_dlp

    duree_max = settings.VIDEO_DUREE_MAX

    def trop_longue(info, *, incomplete):
        duree = info.get('duration')
        return "Vidéo trop longue." if duree and duree > duree_max else None

    options = {
        'quiet': True, 'no_warnings': True, 'noplaylist': True, 'noprogress': True, 'socket_timeout': 30,
        # Vidéo verticale : on limite la largeur (la hauteur dépasse toujours 720). H.264 plutôt que H.265 :
        # plus rapide à décoder ; les images sont de toute façon réduites à 768 px pour Claude
        'format': 'best[ext=mp4][vcodec^=h264][width<=720]/best[ext=mp4][width<=720]/best[ext=mp4]/best',
        'outtmpl': os.path.join(dossier, 'video.%(ext)s'),
        'max_filesize': TAILLE_MAX_VIDEO,
        'match_filter': trop_longue,
    }
    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=True)
    except Exception as e:
        logger.info("Import vidéo : téléchargement impossible de %s (%s)", url, e)
        raise ImportRecetteErreur("Impossible de télécharger cette vidéo. Réessaie plus tard.")

    fichiers = [f for f in os.listdir(dossier) if f.startswith('video.')]
    if not fichiers:
        duree = (info or {}).get('duration')
        if duree and duree > duree_max:
            raise ImportRecetteErreur(f"Vidéo trop longue (plus de {duree_max // 60} minutes).")
        raise ImportRecetteErreur("Impossible de télécharger cette vidéo. Réessaie plus tard.")
    return os.path.join(dossier, fichiers[0])


# ---------- Voix ----------

_modele_whisper = None
_chargement_whisper = threading.Lock()


def _whisper():
    global _modele_whisper
    with _chargement_whisper:
        if _modele_whisper is None:
            from faster_whisper import WhisperModel
            logger.info("Chargement du modèle Whisper %s", settings.WHISPER_MODELE)
            _modele_whisper = WhisperModel(settings.WHISPER_MODELE, device='cpu', compute_type='int8')
        return _modele_whisper


def transcrire(chemin):
    """Texte prononcé dans la vidéo ('' si muette ou seulement de la musique)."""
    try:
        # beam_size=1 : ~2,5 fois plus rapide que la recherche large par défaut, sans perte visible sur des recettes ;
        # WHISPER_LANGUE vide : langue détectée (vidéos en français ou en anglais)
        segments, _ = _whisper().transcribe(chemin, vad_filter=True, beam_size=1, language=settings.WHISPER_LANGUE or None)
        texte = ' '.join(segment.text.strip() for segment in segments)
    except Exception:
        logger.exception("Import vidéo : transcription impossible")
        return ''
    return texte[:TAILLE_MAX_TRANSCRIPTION]


# ---------- Texte à l'écran ----------

def images_cles(chemin):
    """Une image JPEG (octets) toutes les 2 secondes environ, 40 au plus, redimensionnées."""
    import av

    images = []
    try:
        with av.open(chemin) as conteneur:
            flux = conteneur.streams.video[0]
            # décodage sur plusieurs cœurs (~7 fois plus rapide)
            flux.thread_type = 'AUTO'
            duree = float(flux.duration * flux.time_base) if flux.duration else float(conteneur.duration or 0) / av.time_base
            intervalle = max(INTERVALLE_IMAGES_S, duree / NB_MAX_IMAGES) if duree else INTERVALLE_IMAGES_S
            prochaine = 0.0
            for trame in conteneur.decode(flux):
                if trame.time is None or trame.time < prochaine:
                    continue
                image = trame.to_image()
                image.thumbnail((TAILLE_IMAGE, TAILLE_IMAGE))
                tampon = io.BytesIO()
                image.convert('RGB').save(tampon, format='JPEG', quality=80)
                images.append(tampon.getvalue())
                prochaine += intervalle
                if len(images) >= NB_MAX_IMAGES:
                    break
    except Exception:
        logger.exception("Import vidéo : lecture des images impossible")
    return images


def analyser_video(url):
    """(transcription, images JPEG) de la vidéo."""
    with tempfile.TemporaryDirectory(prefix='import-video-') as dossier:
        chemin = telecharger_video(url, dossier)
        # Images extraites pendant la transcription (qui prend l'essentiel du temps)
        with ThreadPoolExecutor(max_workers=1) as extraction:
            images = extraction.submit(images_cles, chemin)
            transcription = transcrire(chemin)
            images = images.result()
    if not transcription and not images:
        raise ImportRecetteErreur("Impossible de lire le contenu de cette vidéo.")
    return transcription, images
