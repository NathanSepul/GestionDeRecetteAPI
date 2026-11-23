from decimal import Decimal
import os
from django.core.files.base import ContentFile
from django.db import IntegrityError, transaction
from django.db.models import Case, F, IntegerField, Max, Value, When
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets, status, generics, permissions
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from gestionDeRecette.api_views import IsOwner
from gestionDeRecette.utils import reorder
from recette.import_web import ImportRecetteErreur, importer_recette_depuis_url, sites_import, titre_libre
from recette.liste_course import generer_liste_course
from recette.models import Recette, Ingredient, Preparation, Produit, Unite
from recette.serializer import (
    RecetteSerializer, ImportRecetteSerializer, ImportUrlSerializer, ImportSiteSerializer, ProduitSerializer, UniteSerializer,
    IngredientSerializer, ReorderIngredientSerializer, PreparationSerializer, ReorderPreparationSerializer,
    ListeCourseRequestSerializer, ListeCourseItemSerializer,
)
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

        # queryset = queryset.filter(user_id=self.request.user.id)
        queryparam_UserId = self.request.GET.get('userId', '')
        queryparam_TypeRecette = self.request.GET.get('typeRecetteId', '')
        queryparam_OrderBy = self.request.GET.get('orderBy', '')
        queryparam_searchTitre = self.request.GET.get('searchTitre', '')
        queryparam_tag = self.request.GET.get('tags')
        
        if queryparam_UserId:
            queryset = queryset.filter(user_id=queryparam_UserId)
        
        if queryparam_TypeRecette:
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
        return Response(ImportSiteSerializer(sites_import(), many=True).data)

    # le serveur télécharge la page et la photo : limité pour ne pas servir de relais de téléchargement
    @action(detail=False, methods=['post'], url_path='import-url', serializer_class=ImportUrlSerializer,
            throttle_classes=[ImportUrlThrottle])
    def import_url(self, request):
        """Importe une recette depuis un site de cuisine (Marmiton...) dans un type de l'utilisateur."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        type_recette = get_object_or_404(TypeRecette, pk=serializer.validated_data['typeRecette'], user=request.user)

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
        recette_id = self.request.query_params.get('recetteId') 
        
        if recette_id:
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
        recette_id = self.request.query_params.get('recetteId') 
        
        if recette_id:
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

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        queryset = super().get_queryset()
        queryparam_produit = self.request.GET.get('searchProduit', '')
        
        if not queryparam_produit:
            return queryset.order_by('nom')

        # Les produits qui commencent par la recherche avant ceux qui la contiennent ailleurs
        queryset = queryset.filter(nom__icontains=queryparam_produit).annotate(
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

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        queryset = super().get_queryset()
        # "pièce" ne sert que d'unité d'achat : sur un ingrédient, "sans unité" veut déjà dire pièces
        return queryset.exclude(code='pièce').order_by('code')