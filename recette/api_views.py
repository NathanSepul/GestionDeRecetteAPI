from decimal import Decimal
import json
import os
from django.core.files.base import ContentFile
from django.db import IntegrityError, transaction
from django.db.models import Case, F, IntegerField, Max, Q, Value, When
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets, status, generics, permissions, serializers
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from gestionDeRecette.api_views import IsOwner
from gestionDeRecette.utils import int_param, reorder
from recette.import_web import ImportRecetteErreur, importer_recette_depuis_url, sites_import, titre_libre
from recette.import_video import est_url_video, lancer_import, sites_video, statut_affiche, verifier_url_video
from recette.liste_course import generer_liste_course
from recette.models import ImportVideo, Recette, Ingredient, Preparation, Produit, Unite
from recette.serializer import (
    RecetteSerializer, EnregistrementRecetteSerializer, ImportRecetteSerializer, ImportUrlSerializer, ImportSiteSerializer, ImportVideoSerializer, ProduitSerializer, UniteSerializer,
    IngredientSerializer, ReorderIngredientSerializer, PreparationSerializer, ReorderPreparationSerializer,
    ListeCourseRequestSerializer, ListeCourseItemSerializer,
)
from tag.models import Tag
from typeRecette.models import TypeRecette



class ImportUrlThrottle(UserRateThrottle):
    """Compteur par utilisateur (taux 'import_url' dans settings.REST_FRAMEWORK)."""
    scope = 'import_url'


@extend_schema(tags=['Recette'])
class RecetteViewSet(viewsets.ModelViewSet):
    queryset = Recette.objects.all()
    serializer_class = RecetteSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwner]
    ORDER_BY_FIELDS = ('id', 'titre', 'portion', 'typeRecette', 'tempsTotal', 'cout', 'difficulte')
    # Champs souvent vides : les recettes sans valeur passent en fin de liste, quel que soit le sens du tri
    ORDER_BY_NULLABLE = ('tempsTotal', 'cout', 'difficulte')

    @staticmethod
    def _liste_entiers(nom, valeur):
        """'1,3' -> [1, 3] (paramètres de filtre)."""
        try:
            return list({int(v.strip()) for v in valeur.split(',') if v.strip()})
        except ValueError:
            raise ValidationError({nom: "Valeurs attendues : des entiers séparés par des virgules."})

    def get_queryset(self):
        queryset = super().get_queryset()

        # Durée totale calculée en SQL pour filtrer / trier ; NULL si aucune durée n'est renseignée
        queryset = queryset.annotate(tempsTotal=Case(
            When(tempsPreparation__isnull=True, tempsCuisson__isnull=True, tempsRepos__isnull=True, then=Value(None)),
            default=Coalesce('tempsPreparation', 0) + Coalesce('tempsCuisson', 0) + Coalesce('tempsRepos', 0),
            output_field=IntegerField(),
        ))

        queryparam_UserId = int_param(self.request, 'userId')
        queryparam_TypeRecette = int_param(self.request, 'typeRecetteId')
        queryparam_OrderBy = self.request.GET.get('orderBy', '')
        queryparam_searchTitre = self.request.GET.get('searchTitre', '')
        queryparam_tag = self.request.GET.get('tags')
        
        if queryparam_UserId is not None:
            queryset = queryset.filter(user_id=queryparam_UserId)

        if queryparam_TypeRecette is not None:
            queryset = queryset.filter(typeRecette=queryparam_TypeRecette)
    
        if queryparam_searchTitre:
            queryset = queryset.filter(titre__icontains=queryparam_searchTitre)

        if queryparam_tag:
            try:
                tag_ids = list(set(int(tag_id.strip()) for tag_id in queryparam_tag.split(',') if tag_id.strip()))
                
                if tag_ids: 
                    for tag_id in tag_ids:
                        queryset = queryset.filter(tags__id=tag_id)
                else:
                    pass 

            except ValueError:
                raise ValidationError({"tags": "Les IDs de tags doivent être des entiers séparés par des virgules."})

        # ?tempsMax=30 : durée totale <= 30 min (les recettes sans durée sont exclues)
        queryparam_tempsMax = self.request.GET.get('tempsMax', '')
        if queryparam_tempsMax:
            try:
                queryset = queryset.filter(tempsTotal__lte=int(queryparam_tempsMax))
            except ValueError:
                raise ValidationError({"tempsMax": "Durée en minutes attendue."})

        # ?cout=1,2 / ?difficulte=1 : un ou plusieurs niveaux
        for champ in ('cout', 'difficulte'):
            valeur = self.request.GET.get(champ, '')
            if valeur:
                queryset = queryset.filter(**{f'{champ}__in': self._liste_entiers(champ, valeur)})

        if queryparam_OrderBy:
            # liste blanche : un champ libre permettrait de trier sur user__password et d'en déduire les hashs
            champ = queryparam_OrderBy.lstrip('-')
            if champ not in self.ORDER_BY_FIELDS:
                raise ValidationError({"orderBy": f"Valeurs autorisées : {', '.join(self.ORDER_BY_FIELDS)} (préfixe '-' pour l'ordre décroissant)."})
            if champ in self.ORDER_BY_NULLABLE:
                expression = F(champ).desc(nulls_last=True) if queryparam_OrderBy.startswith('-') else F(champ).asc(nulls_last=True)
                return queryset.order_by(expression, 'titre')
            return queryset.order_by(queryparam_OrderBy)
        else:
            return queryset.order_by('titre')
        
    def perform_create(self, serializer):
        serializer.validated_data.pop('adapteQuantity', None)
        serializer.save(user=self.request.user)
        
    
    @action(detail=False, methods=['get'], url_path='single_page')
    def single_page(self, request):
        queryset = self.get_queryset()
        
        try:
            page_index = int(request.query_params.get('page', 0))
            instance = queryset[page_index:page_index+1].first()
            
            if not instance:
                return Response({"detail": "Fin de la liste ou page vide."}, status=status.HTTP_404_NOT_FOUND)
                
            serializer = self.get_serializer(instance)
            return Response(serializer.data)
            
        except (ValueError, IndexError):
            return Response({"detail": "Index de page invalide."}, status=status.HTTP_400_BAD_REQUEST)
    
    def _adapt_ingredient_quantities(self, recette_instance, scaling_factor):
        scaling_factor_decimal = Decimal(str(scaling_factor))

        if Decimal(1) != scaling_factor:
            ingredients = list(recette_instance.ingredient_set.filter(isSection=False, quantite__isnull=False))
            for ingredient in ingredients:
                new_quantity = ingredient.quantite * scaling_factor_decimal
                ingredient.quantite = new_quantity.quantize(Decimal('0.01')) # Round to 2 decimal places
            Ingredient.objects.bulk_update(ingredients, ['quantite'])
    
    def update(self, request, *args, **kwargs):
        with transaction.atomic():
            instance = self.get_object()
            old_portion = instance.portion

            # pas de request.data.copy() : copier le QueryDict copie aussi l'image uploadée et plante au-delà de ~2,5 Mo
            serializer = self.get_serializer(instance, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            should_adapt = serializer.validated_data.pop('adapteQuantity', False)
            updated_instance = serializer.save()

            if should_adapt and old_portion and old_portion != 0:
                new_portion = updated_instance.portion
                if new_portion != old_portion:
                    scaling_factor = new_portion / old_portion
                    self._adapt_ingredient_quantities(updated_instance, scaling_factor)

            updated_instance.refresh_from_db()
            return Response(self.get_serializer(updated_instance).data)
   
    # --- Enregistrement complet (écran d'édition) : recette, ingrédients, étapes, tags et image en une transaction ---

    @staticmethod
    def _synchroniser_lignes(modele, recette, lignes, champs):
        """
        Remplace les lignes (ingrédients ou étapes) de la recette par `lignes` : avec id = mise à jour, sans id = création,
        absente = suppression. noOrdre = position dans la liste.
        """
        existantes = {ligne.id: ligne for ligne in modele.objects.filter(recette=recette)}
        gardees = {ligne['id'] for ligne in lignes if ligne.get('id')}
        if gardees - existantes.keys():
            raise ValidationError({modele._meta.model_name: "Ligne inconnue pour cette recette."})

        modele.objects.filter(recette=recette).exclude(id__in=gardees).delete()

        a_modifier, a_creer = [], []
        for ordre, ligne in enumerate(lignes):
            valeurs = {champ: ligne[champ] for champ in champs if champ in ligne}
            if ligne.get('id'):
                objet = existantes[ligne['id']]
                for champ, valeur in valeurs.items():
                    setattr(objet, champ, valeur)
                objet.noOrdre = ordre
                a_modifier.append(objet)
            else:
                a_creer.append(modele(recette=recette, noOrdre=ordre, **valeurs))

        if a_modifier:
            modele.objects.bulk_update(a_modifier, [*champs, 'noOrdre'])
        modele.objects.bulk_create(a_creer)

    def _enregistrer(self, request, instance):
        """
        Corps JSON, ou multipart avec le JSON dans "donnees" et la photo dans "image".
        Tout est enregistré ou rien : une erreur (validation, titre déjà pris...) annule l'ensemble.
        """
        brut = request.data.get('donnees')
        if isinstance(brut, str):
            try:
                brut = json.loads(brut)
            except ValueError:
                raise ValidationError({"donnees": "JSON invalide."})
        elif brut is None:
            brut = request.data

        entree = EnregistrementRecetteSerializer(data=brut)
        entree.is_valid(raise_exception=True)
        donnees = entree.validated_data

        # Image validée avant la transaction, enregistrée en dernier : un échec plus tôt n'écrit aucun fichier
        image = request.FILES.get('image')
        if image:
            image = serializers.ImageField().run_validation(image)

        champs_recette = {k: v for k, v in donnees['recette'].items() if k not in ('image', 'adapteQuantity')}

        try:
            with transaction.atomic():
                ancienne_portion = None
                if instance is not None:
                    # Verrou : deux enregistrements simultanés de la même recette passent l'un après l'autre
                    instance = Recette.objects.select_for_update().get(pk=instance.pk)
                    ancienne_portion = instance.portion

                recette_serializer = RecetteSerializer(instance, data=champs_recette, partial=instance is not None,
                                                       context=self.get_serializer_context())
                recette_serializer.is_valid(raise_exception=True)
                recette_serializer.validated_data.pop('adapteQuantity', None)
                recette = recette_serializer.save(**({} if instance is not None else {'user': request.user}))

                self._synchroniser_lignes(Ingredient, recette, donnees['ingredients'],
                                          ['isSection', 'quantite', 'nom', 'unite', 'produit', 'preparation'])
                if donnees['adapteQuantity'] and ancienne_portion and recette.portion != ancienne_portion:
                    self._adapt_ingredient_quantities(recette, recette.portion / ancienne_portion)

                self._synchroniser_lignes(Preparation, recette, donnees['etapes'], ['isSection', 'description'])

                if donnees['tags'] is not None:
                    ids = set(donnees['tags'])
                    tags = list(Tag.objects.filter(user=request.user, id__in=ids))
                    if len(tags) != len(ids):
                        raise ValidationError({"tags": "Tag inconnu."})
                    recette.tags.set(tags)

                if image:
                    recette.image = image
                    recette.save(update_fields=['image'])
        except IntegrityError:
            return Response(
                {"detail": "Une recette avec ce titre existe déjà pour ce type de recette."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        recette.refresh_from_db()
        return Response({
            'recette': RecetteSerializer(recette, context=self.get_serializer_context()).data,
            'ingredients': IngredientSerializer(recette.ingredient_set.select_related('produit', 'unite').order_by('noOrdre'), many=True).data,
            'etapes': PreparationSerializer(recette.preparation_set.order_by('noOrdre'), many=True).data,
            'tags': sorted(recette.tags.values_list('id', flat=True)),
        }, status=status.HTTP_200_OK if instance is not None else status.HTTP_201_CREATED)

    @extend_schema(request=EnregistrementRecetteSerializer)
    @action(detail=False, methods=['post'], url_path='enregistrer', serializer_class=EnregistrementRecetteSerializer)
    def enregistrer_nouvelle(self, request):
        """Crée une recette complète (recette, ingrédients, étapes, tags, image) en une seule transaction."""
        return self._enregistrer(request, None)

    @extend_schema(request=EnregistrementRecetteSerializer)
    @action(detail=True, methods=['put'], url_path='enregistrer', serializer_class=EnregistrementRecetteSerializer)
    def enregistrer(self, request, pk=None):
        """Remplace une recette complète (recette, ingrédients, étapes, tags, image) en une seule transaction."""
        return self._enregistrer(request, self.get_object())

    @action(detail=False, methods=['post'], url_path='import', serializer_class=ImportRecetteSerializer)
    def import_recette(self, request):
        """Importe une copie d'une recette d'un autre utilisateur (sans le type ni les tags)."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        recette_id = serializer.validated_data['recetteId']
        type_recette_id = serializer.validated_data['typeRecette']

        # La recette source peut appartenir à n'importe quel utilisateur
        source_recette = get_object_or_404(Recette, pk=recette_id)

        # Le type doit obligatoirement appartenir à l'utilisateur connecté
        type_recette = get_object_or_404(TypeRecette, pk=type_recette_id, user=request.user)

        try:
            with transaction.atomic():
                new_recette = Recette.objects.create(
                    user=request.user,
                    # comme l'import depuis un site : "Crêpes (2)" si le titre existe déjà dans ce type
                    titre=titre_libre(source_recette.titre, type_recette),
                    portion=source_recette.portion,
                    typeRecette=type_recette,
                    conseil=source_recette.conseil,
                    source=source_recette.source,
                    tempsPreparation=source_recette.tempsPreparation,
                    tempsCuisson=source_recette.tempsCuisson,
                    tempsRepos=source_recette.tempsRepos,
                    cout=source_recette.cout,
                    difficulte=source_recette.difficulte,
                )

                # Copie de l'image (nouveau fichier physique, pas juste une référence)
                if source_recette.image:
                    new_recette.image.save(
                        os.path.basename(source_recette.image.name),
                        ContentFile(source_recette.image.read()),
                        save=True,
                    )

                Ingredient.objects.bulk_create([
                    Ingredient(
                        recette=new_recette,
                        noOrdre=ingredient.noOrdre,
                        isSection=ingredient.isSection,
                        quantite=ingredient.quantite,
                        nom=ingredient.nom,
                        unite_id=ingredient.unite_id,
                        produit_id=ingredient.produit_id,
                        preparation=ingredient.preparation,
                    )
                    for ingredient in source_recette.ingredient_set.order_by('noOrdre')
                ])

                Preparation.objects.bulk_create([
                    Preparation(
                        recette=new_recette,
                        noOrdre=preparation.noOrdre,
                        isSection=preparation.isSection,
                        description=preparation.description,
                    )
                    for preparation in source_recette.preparation_set.order_by('noOrdre')
                ])

        except IntegrityError:
            # deux copies simultanées du même titre : titre_libre ne peut pas l'empêcher à 100 %
            return Response(
                {"detail": "Une recette avec ce titre existe déjà pour ce type de recette."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result_serializer = RecetteSerializer(new_recette, context={'request': request})
        return Response(result_serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(request=None, responses={200: ImportSiteSerializer(many=True)})
    @action(detail=False, methods=['get'], url_path='import-sites', pagination_class=None)
    def import_sites(self, request):
        """Sites dont on peut importer les recettes (nom, domaine, adresse), pour les lister dans l'interface."""
        return Response(ImportSiteSerializer(sites_import(), many=True).data + sites_video())

    @extend_schema(request=None, responses={200: ImportVideoSerializer})
    @action(detail=False, methods=['get'], url_path=r'import-video/(?P<import_id>\d+)', pagination_class=None)
    def import_video(self, request, import_id=None):
        """Avancement d'un import vidéo de l'utilisateur."""
        tache = get_object_or_404(ImportVideo, pk=import_id, user=request.user)
        donnees = ImportVideoSerializer(tache).data
        donnees['statut'], donnees['erreur'] = statut_affiche(tache)
        return Response(donnees)

    # le serveur télécharge la page et la photo : limité pour ne pas servir de relais de téléchargement
    @action(detail=False, methods=['post'], url_path='import-url', serializer_class=ImportUrlSerializer,
            throttle_classes=[ImportUrlThrottle])
    def import_url(self, request):
        """Importe une recette depuis un site de cuisine (Marmiton...) dans un type de l'utilisateur."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        type_recette = get_object_or_404(TypeRecette, pk=serializer.validated_data['typeRecette'], user=request.user)
        url = serializer.validated_data['url']

        # Vidéo (TikTok) : traitée en arrière-plan, le client suit l'avancement via import-video/<id>/
        if est_url_video(url):
            try:
                verifier_url_video(url)
            except ImportRecetteErreur as e:
                return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
            tache = ImportVideo.objects.create(
                user=request.user, url=url, typeRecette=type_recette,
                importerImage=serializer.validated_data['importerImage'],
            )
            lancer_import(tache)
            return Response({'importVideo': ImportVideoSerializer(tache).data}, status=status.HTTP_202_ACCEPTED)

        try:
            recette = importer_recette_depuis_url(
                serializer.validated_data['url'], request.user, type_recette,
                importer_image=serializer.validated_data['importerImage'],
            )
        except ImportRecetteErreur as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(RecetteSerializer(recette, context={'request': request}).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=['post'], url_path='liste-course', serializer_class=ListeCourseRequestSerializer)
    def liste_course(self, request):
        """Génère la liste de course agrégée (par produit) pour une recette et un nombre de portions donné."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        recette = get_object_or_404(Recette, pk=serializer.validated_data['recetteId'])
        results = generer_liste_course({recette: serializer.validated_data['portion']})

        result_serializer = ListeCourseItemSerializer(results, many=True)
        return Response(result_serializer.data, status=status.HTTP_200_OK)
########################
########################

@extend_schema(tags=['Ingredient'])
class IngredientViewSet(viewsets.ModelViewSet):
    # select_related : évite 2 requêtes par ingrédient pour produit_detail / unite_detail
    queryset = Ingredient.objects.select_related('produit', 'unite')
    serializer_class = IngredientSerializer
    pagination_class = None
    permission_classes = [permissions.IsAuthenticated,IsOwner]
    
    def get_queryset(self):
        """
        Filtre par recette_id si passé en paramètre (?recetteId=...)
        Sinon renvoie tout (pour l'admin ou debug)
        """
        queryset = self.queryset
        recette_id = int_param(self.request, 'recetteId')

        if recette_id is not None:
            queryset = queryset.filter(recette_id=recette_id)
        
        return queryset.order_by('noOrdre')
    
    def perform_create(self, serializer):
        """Assigne automatiquement l'utilisateur lors de la création."""
        recette_instance = serializer.validated_data.get('recette')

        if recette_instance.user_id != self.request.user.id:
            raise PermissionDenied("Vous n'êtes pas propriétaire de cette recette.")

        max_no_ordre = Ingredient.objects.filter(recette=recette_instance).aggregate(Max('noOrdre'))['noOrdre__max']
        next_no_ordre = (max_no_ordre + 1) if max_no_ordre is not None else 0
        serializer.save(noOrdre=next_no_ordre)

    def perform_update(self, serializer):
        """Empêche de déplacer l'ingrédient vers la recette d'un autre utilisateur."""
        recette_instance = serializer.validated_data.get('recette')

        if recette_instance and recette_instance.user_id != self.request.user.id:
            raise PermissionDenied("Vous n'êtes pas propriétaire de cette recette.")

        serializer.save()

    @action(detail=True, methods=['post'], serializer_class=ReorderIngredientSerializer)
    def reorder(self, request, pk=None):
        """Réorganise l'ordre d'une étape spécifique."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            ingredient_to_move = self.get_object()
            siblings = Ingredient.objects.filter(recette_id=ingredient_to_move.recette_id)
            new_ordered_list = reorder(ingredient_to_move, siblings, serializer.validated_data["newPosition"])

        result_serializer = IngredientSerializer(new_ordered_list, many=True)
        return Response(result_serializer.data, status=status.HTTP_200_OK)


########################
########################


@extend_schema(tags=['Preparation'])
class PreparationViewSet(viewsets.ModelViewSet):
    queryset = Preparation.objects.all()
    serializer_class = PreparationSerializer
    pagination_class = None
    permission_classes = [permissions.IsAuthenticated,IsOwner]
    
    def get_queryset(self):
        """
        Filtre par recette_id si passé en paramètre (?recetteId=...)
        Sinon renvoie tout (pour l'admin ou debug)
        """
        queryset = self.queryset
        recette_id = int_param(self.request, 'recetteId')

        if recette_id is not None:
            queryset = queryset.filter(recette_id=recette_id)
        
        return queryset.order_by('noOrdre')
    
    def perform_create(self, serializer):
        """Assigne automatiquement l'utilisateur lors de la création."""
        recette_instance = serializer.validated_data.get('recette')

        if recette_instance.user_id != self.request.user.id:
            raise PermissionDenied("Vous n'êtes pas propriétaire de cette recette.")

        max_no_ordre = Preparation.objects.filter(recette=recette_instance).aggregate(Max('noOrdre'))['noOrdre__max']
        next_no_ordre = (max_no_ordre + 1) if max_no_ordre is not None else 0
        serializer.save(noOrdre=next_no_ordre)

    def perform_update(self, serializer):
        """Empêche de déplacer la préparation vers la recette d'un autre utilisateur."""
        recette_instance = serializer.validated_data.get('recette')

        if recette_instance and recette_instance.user_id != self.request.user.id:
            raise PermissionDenied("Vous n'êtes pas propriétaire de cette recette.")

        serializer.save()

    @action(detail=True, methods=['post'], serializer_class=ReorderPreparationSerializer)
    def reorder(self, request, pk=None):
        """Réorganise l'ordre d'une étape spécifique."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            preparation_to_move = self.get_object()
            siblings = Preparation.objects.filter(recette_id=preparation_to_move.recette_id)
            new_ordered_list = reorder(preparation_to_move, siblings, serializer.validated_data["newPosition"])

        result_serializer = PreparationSerializer(new_ordered_list, many=True)
        return Response(result_serializer.data, status=status.HTTP_200_OK)
    
############
###########


@extend_schema(tags=['Produit'])
class ProduitListAPIView(generics.ListAPIView):
    queryset = Produit.objects.all()
    serializer_class = ProduitSerializer
    paginator = None

    def get_queryset(self):
        # produits "à vérifier" (import massif) : pas proposés tant qu'ils ne sont pas validés dans l'admin
        queryset = super().get_queryset().filter(statut=Produit.Statut.VALIDE)
        queryparam_produit = self.request.GET.get('searchProduit', '')
        
        if not queryparam_produit:
            return queryset.order_by('nom')

        # Nom ou synonyme ("poireaux" trouve "poireau") ; ceux qui commencent par la recherche d'abord
        queryset = queryset.filter(
            Q(nom__icontains=queryparam_produit) | Q(synonymes__texte__icontains=queryparam_produit)
        ).distinct().annotate(
            pertinence=Case(When(nom__istartswith=queryparam_produit, then=0), default=1, output_field=IntegerField())
        ).order_by('pertinence', 'nom')

        # Limite optionnelle (?limit=) : sans paramètre, tous les résultats (comportement attendu par l'app Flutter)
        try:
            limit = int(self.request.GET.get('limit', 0))
        except ValueError:
            limit = 0
        return queryset[:limit] if limit > 0 else queryset
    

############
###########


@extend_schema(tags=['Unite'])
class UniteListAPIView(generics.ListAPIView):
    queryset = Unite.objects.all()
    serializer_class = UniteSerializer
    paginator = None

    def get_queryset(self):
        queryset = super().get_queryset()
        # "pièce" ne sert que d'unité d'achat : sur un ingrédient, "sans unité" veut déjà dire pièces
        return queryset.exclude(code='pièce').order_by('code')