from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.http import HttpResponse
from weasyprint import HTML
from tag.models import Tag
from .models import Recette, Ingredient, Preparation
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny

@api_view(['GET'])
@permission_classes([AllowAny])
def generer_pdf(request, recette_id):
    recette = get_object_or_404(Recette, pk=recette_id)
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
    filename = f"{recette.titre}.pdf"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response