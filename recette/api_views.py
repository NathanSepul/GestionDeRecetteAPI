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
                        queryset = queryset.filter(tag__id=tag_id)
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
        recette_instance = serializer.validated_data.get('recette')
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
        recette_instance = serializer.validated_data.get('recette')
        max_no_ordre = Preparation.objects.filter( recette=recette_instance).aggregate(Max('noOrdre'))['noOrdre__max']
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