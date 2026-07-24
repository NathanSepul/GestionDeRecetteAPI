from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from django.http import HttpResponse
from weasyprint import HTML
from recette.models import Recette, Ingredient, Preparation

def generer_pdf(request, recette_id):
    recette = get_object_or_404(Recette, pk=recette_id)
    ingredients = Ingredient.objects.filter(recette=recette).order_by('noOrdre')
    preparations = Preparation.objects.filter(recette=recette).order_by('noOrdre')

    contexte = {
        "recette": recette,
        "ingredients": ingredients,
        "preparations": preparations,
    }

    html_string = render_to_string("pdf/recette.html", contexte, request=request)
    pdf = HTML(string=html_string, base_url=request.build_absolute_uri()).write_pdf()

    response = HttpResponse(pdf, content_type="application/pdf")
    filename = f"{recette.titre}.pdf"
    response["Content-Disposition"] = f'inline; filename="{filename}"'
    # Utilise 'attachment' au lieu de 'inline' pour forcer le téléchargement direct
    return response