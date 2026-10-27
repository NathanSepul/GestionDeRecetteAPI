from django.core.management.base import BaseCommand

from gestionDeRecette.images import generate_variants
from recette.models import Recette
from typeRecette.models import TypeRecette
from user.models import User


class Command(BaseCommand):
    help = "Génère les variantes redimensionnées (WebP) des images déjà uploadées."

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Régénère aussi les variantes existantes.")

    def handle(self, *args, force=False, **options):
        sources = [(Recette, "image"), (TypeRecette, "image"), (User, "avatar")]

        for model, field_name in sources:
            done = failed = 0
            for obj in model.objects.exclude(**{field_name: ""}).exclude(**{f"{field_name}__isnull": True}).iterator():
                file = getattr(obj, field_name)
                try:
                    generate_variants(file.path, force=force)
                    done += 1
                except Exception as e:
                    failed += 1
                    self.stderr.write(f"{model.__name__} #{obj.pk} ({file.name}) : {e}")

            self.stdout.write(self.style.SUCCESS(f"{model.__name__} : {done} image(s) traitée(s), {failed} échec(s)"))
