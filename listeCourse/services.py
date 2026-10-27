from django.db import transaction
from listeCourse.models import ListeCourseArticle
from recette.liste_course import generer_liste_course


def _cle(produit_id, nom, unite_id):
    return (produit_id, None if produit_id else (nom or '').strip().lower(), unite_id)


@transaction.atomic
def regenerer_articles(liste):
    """
    Recalcule les articles générés à partir des recettes de la liste.
    Un article déjà coché le reste, sauf si sa quantité augmente (il faut en racheter).
    Les articles ajoutés à la main ne sont pas touchés.
    """
    anciens = {
        _cle(a.produit_id, a.nom, a.unite_id): a
        for a in liste.articles.filter(manuel=False)
    }
    portions = {lr.recette: lr.portion for lr in liste.recettes.select_related('recette')}
    lignes = generer_liste_course(portions) if portions else []

    nouveaux = []
    for ligne in lignes:
        produit, unite = ligne['produit'], ligne['unite']
        ancien = anciens.get(_cle(produit.pk if produit else None, ligne['nom'], unite.pk if unite else None))
        quantite = ligne['quantite']
        coche = bool(ancien and ancien.coche and (
            quantite is None or (ancien.quantite is not None and quantite <= ancien.quantite)
        ))
        nouveaux.append(ListeCourseArticle(
            liste=liste, produit=produit, nom=ligne['nom'], precision=ligne['precision'], unite=unite,
            quantite=quantite, rayon=ligne['rayon'], placard=ligne['placard'], coche=coche,
        ))

    liste.articles.filter(manuel=False).delete()
    ListeCourseArticle.objects.bulk_create(nouveaux)
    liste.save(update_fields=['dateModification'])
