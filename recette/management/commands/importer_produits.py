"""
Ajoute au référentiel les produits de recette/donnees/produits_openfoodfacts.json (taxonomie Open Food Facts, triée et
complétée par Claude Haiku) : statut "à vérifier", donc invisibles dans la recherche et l'analyse des imports tant
qu'ils ne sont pas validés dans l'admin (action "Valider").

N'ajoute que ce qui manque (nom, pluriel ou synonyme déjà connu : ignoré) : relançable sans risque.
    ./manage.py importer_produits [--essai]
"""
import json
from decimal import Decimal
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction

from recette.models import Equivalence, Produit, Rayon, Synonyme, Unite, normaliser_nom

FICHIER = Path(__file__).resolve().parents[2] / 'donnees' / 'produits_openfoodfacts.json'


class Command(BaseCommand):
    help = "Ajoute les produits Open Food Facts (à vérifier) au référentiel."

    def add_arguments(self, parser):
        parser.add_argument('--essai', action='store_true', help="Affiche ce qui serait ajouté, sans rien enregistrer.")
        parser.add_argument('--fichier', default=str(FICHIER))

    def handle(self, *args, essai=False, fichier=None, **options):
        fiches = json.loads(Path(fichier).read_text(encoding='utf-8'))
        rayons = {r.nom: r for r in Rayon.objects.all()}
        unites = {u.code: u for u in Unite.objects.all()}
        g, ml = unites.get('g'), unites.get('ml')

        connus = set(Synonyme.objects.values_list('cle', flat=True))
        for nom, pluriel in Produit.objects.values_list('nom', 'nomPluriel'):
            connus |= {normaliser_nom(nom), normaliser_nom(pluriel)}

        with transaction.atomic():
            crees = {}
            # Produits de base d'abord : un dérivé pointe vers sa base
            for fiche in sorted(fiches, key=lambda f: f['produitDeBase'] is not None):
                if normaliser_nom(fiche['nom']) in connus:
                    continue
                base = None
                if fiche['produitDeBase']:
                    base = crees.get(fiche['produitDeBase']) or Produit.objects.filter(nom=fiche['produitDeBase']).first()
                produit = Produit.objects.create(
                    nom=fiche['nom'], nomPluriel=fiche['nomPluriel'] or fiche['nom'], rayon=rayons.get(fiche['rayon']),
                    placard=fiche['placard'], uniteAchat=unites.get(fiche['uniteAchat']), produitDeBase=base,
                    statut=Produit.Statut.A_VERIFIER, source=Produit.Source.OPEN_FOOD_FACTS,
                )
                crees[produit.nom] = produit
                connus |= {normaliser_nom(produit.nom), normaliser_nom(produit.nomPluriel)}
                if fiche['poidsPieceG'] and g:
                    Equivalence.objects.create(produit=produit, quantite=1, unite=None,
                                               quantiteCible=Decimal(str(fiche['poidsPieceG'])), uniteCible=g)
                if fiche['densiteGParMl'] and g and ml:
                    Equivalence.objects.create(produit=produit, quantite=1, unite=ml,
                                               quantiteCible=Decimal(str(fiche['densiteGParMl'])).quantize(Decimal('0.001')), uniteCible=g)
                for texte in fiche['synonymes']:
                    if normaliser_nom(texte) not in connus:
                        Synonyme.objects.create(texte=texte, produit=produit)
                        connus.add(normaliser_nom(texte))

            self.stdout.write(f"{len(crees)} produits ajoutés (à vérifier), {len(fiches) - len(crees)} déjà connus.")
            if essai:
                transaction.set_rollback(True)
                self.stdout.write("Essai : rien n'a été enregistré.")
