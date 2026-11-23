import os
from pathlib import Path
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.http import HttpResponse
from django.utils.http import content_disposition_header
from weasyprint import HTML
from tag.models import Tag
from .models import Recette, Ingredient, Preparation
from rest_framework.decorators import api_view
from drf_spectacular.utils import extend_schema
from drf_spectacular.types import OpenApiTypes
from gestionDeRecette.images import variant_name


def _image_uri(recette):
    """
    Image lue directement sur le disque (file://) : en prod, /media/ exige d'être connecté
    et WeasyPrint, qui n'envoie pas le token, recevrait une 401. La variante "medium" suffit et allège le PDF.
    """
    if not recette.image:
        return None
    chemin = recette.image.path
    medium = variant_name(chemin, 'medium')
    if os.path.isfile(medium):
        chemin = medium
    return Path(chemin).as_uri() if os.path.isfile(chemin) else None

@extend_schema(
    tags=['Recette'],
    responses={200: OpenApiTypes.BINARY},
    description="Génère le PDF de la recette"
)
@api_view(['GET'])
def generer_pdf(request, id):
    # Réservé aux utilisateurs connectés (JWT, comme le reste de l'API)
    recette = get_object_or_404(Recette, pk=id)
    ingredients = Ingredient.objects.filter(recette=recette).select_related('produit', 'unite').order_by('noOrdre')
    preparations = Preparation.objects.filter(recette=recette).order_by('noOrdre')

    tags_recette = Tag.objects.filter(recettes=recette)
    tags = []
    for tag in tags_recette:
        alpha = tag.opacite / 255

        fond_r = alpha * tag.red + (1 - alpha) * 255
        fond_g = alpha * tag.green + (1 - alpha) * 255
        fond_b = alpha * tag.blue + (1 - alpha) * 255
        luminosite = (fond_r * 299 + fond_g * 587 + fond_b * 114) / 1000
        couleur_texte = "#ffffff" if luminosite < 140 else "#1a1a1a"

        tags.append({
            "nom": tag.tag,
            "style": f"background-color: rgba({tag.red}, {tag.green}, {tag.blue}, {alpha}); color: {couleur_texte};",
        })

    compteur = 0
    preparations_numerotees = []
    for preparation in preparations:
        if preparation.isSection:
            numero = None
        else:
            compteur += 1
            numero = compteur

        preparations_numerotees.append({
            "isSection": preparation.isSection,
            "description": preparation.description,
            "numero": numero,
        })

    contexte = {
        "recette": recette,
        "image_uri": _image_uri(recette),
        "ingredients": ingredients,
        "preparations": preparations_numerotees,
        "tags": tags,
    }

    html_string = render_to_string("pdf/recette.html", contexte, request=request)

# --- DEBUG 
    # return HttpResponse(html_string, content_type="text/html")

    # --- Prod
    pdf = HTML(string=html_string, base_url=request.build_absolute_uri()).write_pdf()
    response = HttpResponse(pdf, content_type="application/pdf")
    # gère guillemets et accents dans le titre (filename*=UTF-8...)
    response["Content-Disposition"] = content_disposition_header(True, f"{recette.titre}.pdf")
    return response