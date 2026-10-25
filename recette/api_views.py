from decimal import Decimal
from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import viewsets, status, generics, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from gestionDeRecette.api_views import IsOwner
from recette.models import *
from recette.serializer import  *
from django.db.models import Max

import os
from django.core.files.base import ContentFile
from django.shortcuts import get_object_or_404
from django.db import IntegrityError
from typeRecette.models import TypeRecette

    
@extend_schema(tags=['Recette'])
class RecetteViewSet(viewsets.ModelViewSet):
    queryset = Recette.objects.all()
    serializer_class = RecetteSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwner]
    
    def get_queryset(self):
        queryset = super().get_queryset()

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
                from rest_framework.exceptions import ValidationError
                raise ValidationError({"tags": "Les IDs de tags doivent être des entiers séparés par des virgules."})
        
       
        if queryparam_OrderBy:
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
            for ingredient in recette_instance.ingredient_set.all():
                if ingredient.quantite is not None and not ingredient.isSection:
                    new_quantity = ingredient.quantite * scaling_factor_decimal
                    ingredient.quantite = new_quantity.quantize(Decimal('0.01')) # Round to 2 decimal places
                    ingredient.save()
    
    def update(self, request, *args, **kwargs):
        try:    
            with transaction.atomic():
                instance = self.get_object()
                old_portion = instance.portion

                data = request.data.copy()
                adapte_val = data.pop("adapteQuantity", [False])
                if isinstance(adapte_val, list): adapte_val = adapte_val[0]
                should_adapt = str(adapte_val).lower() == 'true'
                
                serializer = self.get_serializer(instance, data=data, partial=True)
                serializer.is_valid(raise_exception=True)
                updated_instance = serializer.save()
                
                if should_adapt and old_portion and old_portion != 0:
                    new_portion = updated_instance.portion
                    if new_portion != old_portion:
                        scaling_factor = new_portion / old_portion    
                        self._adapt_ingredient_quantities(updated_instance, scaling_factor)
                        
                updated_instance.refresh_from_db()
                return Response(self.get_serializer(updated_instance).data)
        except Exception as e:
            return Response(f"An error occurred during update recette: {e}", status=status.HTTP_400_BAD_REQUEST)
   
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
                    titre=source_recette.titre,
                    portion=source_recette.portion,
                    typeRecette=type_recette,
                    conseil=source_recette.conseil,
                )

                # Copie de l'image (nouveau fichier physique, pas juste une référence)
                if source_recette.image:
                    new_recette.image.save(
                        os.path.basename(source_recette.image.name),
                        ContentFile(source_recette.image.read()),
                        save=True,
                    )

                # Copie des ingrédients
                for ingredient in source_recette.ingredient_set.all().order_by('noOrdre'):
                    Ingredient.objects.create(
                        recette=new_recette,
                        noOrdre=ingredient.noOrdre,
                        isSection=ingredient.isSection,
                        quantite=ingredient.quantite,
                        nom=ingredient.nom,
                        unite=ingredient.unite,
                        produit=ingredient.produit,
                    )

                # Copie des préparations
                for preparation in source_recette.preparation_set.all().order_by('noOrdre'):
                    Preparation.objects.create(
                        recette=new_recette,
                        noOrdre=preparation.noOrdre,
                        isSection=preparation.isSection,
                        description=preparation.description,
                    )

        except IntegrityError:
            return Response(
                {"detail": "Une recette avec ce titre existe déjà pour ce type de recette."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result_serializer = RecetteSerializer(new_recette)
        return Response(result_serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['post'], url_path='liste-course', serializer_class=ListeCourseRequestSerializer)
    def liste_course(self, request):
        """Génère la liste de course agrégée (par produit) pour une recette et un nombre de portions donné."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        recette = get_object_or_404(Recette, pk=serializer.validated_data['recetteId'])
        desired_portion = serializer.validated_data['portion']

        scaling_factor = (
            Decimal(desired_portion) / Decimal(recette.portion)
            if recette.portion else Decimal(1)
        )

        aggregated = {}
        
        for ingredient in recette.ingredient_set.filter(isSection=False):
            if ingredient.quantite is not None:
                scaled_qty = (ingredient.quantite * scaling_factor).quantize(Decimal('0.01'))
            else:
                scaled_qty = None  # ex: "sel, au goût" -> pas de quantité à sommer

            if ingredient.produit_id:
                key = ('produit', ingredient.produit_id, ingredient.unite_id)
            else:
                key = ('nom', ingredient.nom, ingredient.unite_id)

            if key not in aggregated:
                aggregated[key] = {
                    'produit': ingredient.produit,
                    'nom': ingredient.nom if not ingredient.produit_id else None,
                    'unite': ingredient.unite,
                    'quantite': None,
                }

            if scaled_qty is not None:
                current = aggregated[key]['quantite']
                aggregated[key]['quantite'] = scaled_qty if current is None else current + scaled_qty

        results = list(aggregated.values())
        results.sort(key=lambda x: (x['produit'].nom if x['produit'] else (x['nom'] or '')).lower())

        result_serializer = ListeCourseItemSerializer(results, many=True)
        return Response(result_serializer.data, status=status.HTTP_200_OK)
########################
########################

@extend_schema(tags=['Ingredient'])
class IngredientViewSet(viewsets.ModelViewSet):
    queryset = Ingredient.objects.all()
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
        from rest_framework.exceptions import PermissionDenied
        recette_instance = serializer.validated_data.get('recette')

        if recette_instance.user_id != self.request.user.id:
            raise PermissionDenied("Vous n'êtes pas propriétaire de cette recette.")

        max_no_ordre = Ingredient.objects.filter(recette=recette_instance).aggregate(Max('noOrdre'))['noOrdre__max']
        next_no_ordre = (max_no_ordre + 1) if max_no_ordre is not None else 0
        serializer.save(noOrdre=next_no_ordre)
    
    @action(detail=True, methods=['post'], serializer_class=ReorderIngredientSerializer)
    def reorder(self, request, pk=None):
        """Réorganise l'ordre d'une étape spécifique."""
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            new_position = serializer.validated_data["newPosition"]

            with transaction.atomic():
                ingredient_to_move = self.get_object()
                current_recette_id = ingredient_to_move.recette_id

                ingredients_to_reorder = Ingredient.objects.filter(
                    recette_id=current_recette_id
                ).exclude(id=ingredient_to_move.id).order_by('noOrdre')

                new_ordered_list = []
                if new_position == 0:
                    new_ordered_list.append(ingredient_to_move)

                for i, ing in enumerate(ingredients_to_reorder):
                    new_ordered_list.append(ing)
                    if i + 1 == new_position:
                        new_ordered_list.append(ingredient_to_move)

                for index, ing in enumerate(new_ordered_list):
                    ing.noOrdre = index
                    ing.save()
                    
            result_serializer = IngredientSerializer(new_ordered_list, many=True)
            return Response(result_serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"detail": f"Erreur : {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


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
        from rest_framework.exceptions import PermissionDenied

        recette_instance = serializer.validated_data.get('recette')

        if recette_instance.user_id != self.request.user.id:
            raise PermissionDenied("Vous n'êtes pas propriétaire de cette recette.")

        max_no_ordre = Preparation.objects.filter(recette=recette_instance).aggregate(Max('noOrdre'))['noOrdre__max']
        next_no_ordre = (max_no_ordre + 1) if max_no_ordre is not None else 0
        serializer.save(noOrdre=next_no_ordre)
        
    @action(detail=True, methods=['post'], serializer_class=ReorderPreparationSerializer)
    def reorder(self, request, pk=None):
        """Réorganise l'ordre d'une étape spécifique."""
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            new_position = serializer.validated_data["newPosition"]

            with transaction.atomic():
                preparation_to_move = self.get_object()
                current_recette_id = preparation_to_move.recette_id

                preparations_to_reorder = Preparation.objects.filter(
                    recette_id=current_recette_id
                ).exclude(id=preparation_to_move.id).order_by('noOrdre')

                new_ordered_list = []
                if new_position == 0:
                    new_ordered_list.append(preparation_to_move)

                for i, prep in enumerate(preparations_to_reorder):
                    new_ordered_list.append(prep)
                    if i + 1 == new_position:
                        new_ordered_list.append(preparation_to_move)

                for index, prep in enumerate(new_ordered_list):
                    prep.noOrdre = index
                    prep.save()
                    
            result_serializer = PreparationSerializer(new_ordered_list, many=True)
            return Response(result_serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {"detail": f"Erreur : {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
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
        
        if queryparam_produit:
            queryset = queryset.filter(nom__icontains=queryparam_produit)
        
        return queryset.order_by('nom')
    

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
        return queryset.order_by('code')