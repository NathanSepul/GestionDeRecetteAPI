"""
Variantes redimensionnées (WebP) des images uploadées.

Chaque image `photos/tarte_ab12cd34.jpg` est accompagnée de :
    photos/tarte_ab12cd34_thumb.webp   (listes, cartes, avatars)
    photos/tarte_ab12cd34_medium.webp  (bannière de la page détail)

Les noms sont déduits de l'original : pas de champ ni de migration à ajouter.
Tant qu'une variante n'existe pas (image antérieure non traitée), l'URL de l'original est renvoyée.
"""
import os

from PIL import Image, ImageOps

VARIANTS = {
    "thumb": 400,
    "medium": 1200,
}
WEBP_QUALITY = 80


def variant_name(name, variant):
    root, _ = os.path.splitext(name)
    return f"{root}_{variant}.webp"


def generate_variants(path, force=False):
    """Crée les variantes manquantes d'une image (ou toutes avec force=True)."""
    if not path or not os.path.isfile(path):
        return

    targets = {v: variant_name(path, v) for v in VARIANTS}
    if not force and all(os.path.isfile(p) for p in targets.values()):
        return

    with Image.open(path) as img:
        # Applique la rotation EXIF des photos de téléphone avant de perdre les métadonnées
        img = ImageOps.exif_transpose(img)
        img = img.convert("RGBA" if img.mode in ("RGBA", "LA", "P") else "RGB")

        for variant, max_size in VARIANTS.items():
            copy = img.copy()
            copy.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            copy.save(targets[variant], "WEBP", quality=WEBP_QUALITY)


def delete_variants(path):
    for variant in VARIANTS:
        variant_path = variant_name(path, variant)
        if os.path.isfile(variant_path):
            os.remove(variant_path)


def variant_url(field, variant, request=None):
    """URL de la variante si elle existe, sinon de l'original (None s'il n'y a pas d'image)."""
    if not field:
        return None

    url = field.url
    if os.path.isfile(variant_name(field.path, variant)):
        url = variant_name(url, variant)

    return request.build_absolute_uri(url) if request else url
