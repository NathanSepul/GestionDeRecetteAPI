from decimal import Decimal
from rest_framework import generics
from rest_framework.response import Response
from rest_framework import status
import recette
import recette.models
import recette.serializer
from django.db import transaction
from rest_framework.views import APIView 
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema
import base64

@extend_schema(tags=['Recette'])
class RecetteListLiteAPIView(generics.ListAPIView):
    queryset = recette.models.Recette.objects.all()
    serializer_class = recette.serializer.RecetteLiteSerializer
    paginator = None

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(user_id=self.request.user.id)
        queryparam_TypeRecette = self.request.GET.get('typeRecetteId', '')
        
        if queryparam_TypeRecette:
            queryset = queryset.filter(typeRecette=queryparam_TypeRecette)
        
        return queryset.order_by('titre')

@extend_schema(tags=['Recette'])
class RecetteListAPIView(generics.ListAPIView):
    """
    list of recette
    """

    queryset = recette.models.Recette.objects.all()
    serializer_class = recette.serializer.RecetteSerializer

    @extend_schema(
        operation_id='get list recette',
        description='get list recette',
        # security=[],
    )   
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    def get_queryset(self):
        queryset = super().get_queryset()

        queryset = queryset.filter(user_id=self.request.user.id)

        queryparam_TypeRecette = self.request.GET.get('typeRecetteId', '')
        queryparam_OrderBy = self.request.GET.get('orderBy', '')
        queryparam_searchTitre = self.request.GET.get('searchTitre', '')
        queryparam_tag = self.request.GET.get('tags')
        
        if queryparam_TypeRecette:
            queryset = queryset.filter(typeRecette=queryparam_TypeRecette)
    
        if queryparam_searchTitre:
            queryset = queryset.filter(titre__icontains=queryparam_searchTitre)

        if queryparam_tag:
            try:
                tag_ids = list(set(int(tag_id.strip()) for tag_id in queryparam_tag.split(',') if tag_id.strip()))
                
                if tag_ids: 
                    # queryset = queryset.filter(tag__in=tag_ids)
                    # queryset = queryset.distinct()
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
        
@extend_schema(tags=['Recette'])
class RecetteRetrieveAPIView(generics.RetrieveAPIView):
    """
    Returns the **selected** Recette informations.
    """

    queryset = recette.models.Recette.objects.all()
    serializer_class = recette.serializer.RecetteSerializer

    # @swagger_auto_schema(operation_id='Get recette by id', security=[],)
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
@extend_schema(tags=['Recette'])
class RecetteCreateAPIView(generics.CreateAPIView):
    """
    Create Recette
    """

    queryset = recette.models.Recette.objects.all()
    serializer_class = recette.serializer.RecetteSerializer

    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs) 
       
@extend_schema(tags=['Recette'])
class RecetteDeleteAPIView(generics.DestroyAPIView):
    queryset = recette.models.Recette.objects.all()
    serializer_class = recette.serializer.RecetteSerializer

    def delete(self, request, pk, format=None):
        recette = self.get_object()
        recette.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

@extend_schema(tags=['Recette'])  
class RecetteUpdateAPIView(generics.UpdateAPIView):
    queryset = recette.models.Recette.objects.all()
    serializer_class = recette.serializer.RecetteSerializer

    def _adapt_ingredient_quantities(self, recette_instance, scaling_factor):
        if 1 != scaling_factor:
            for ingredient in recette_instance.ingredients.all():
                if ingredient.quantite is not None and not ingredient.isSection:
                    new_quantity = ingredient.quantite * scaling_factor
                    ingredient.quantite = new_quantity.quantize(Decimal('0.01')) # Round to 2 decimal places
                    ingredient.save() # Save the updated ingredient

    def update(self, request, *args, **kwargs):
        with transaction.atomic():
            try:
                instance = self.get_object()
                old_portion = instance.portion

                image_base64_string = request.data.pop("image", None)
                
                serializer = self.get_serializer(instance, data=request.data, partial=True)
                serializer.is_valid(raise_exception=True)
                serializer.save()

                if image_base64_string:
                    instance.image = base64.b64decode(image_base64_string)
                else:
                    instance.image = None
                        
                if request.data.get("adapteQuantity"):
                    if old_portion != 0: 
                        scaling_factor = instance.portion / old_portion    
                        self._adapt_ingredient_quantities(instance, scaling_factor)

                instance.save()
                return Response("Recette updated", status=status.HTTP_200_OK)
            except Exception as e:
               return Response(f"An error occurred during update recette: {e}", status=status.HTTP_400_BAD_REQUEST)
                
########################
########################

@extend_schema(tags=['Ingredient'])
class IngredientRetrieveAPIView(generics.ListAPIView):
    """
    list of ingredientt
    """

    queryset = recette.models.Ingredient.objects.all()
    serializer_class = recette.serializer.IngredientSerializer
    paginator = None

    # @swagger_auto_schema(operation_id='Get comments', security=[],)
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(recette__id=self.kwargs["pk"])
        return queryset.order_by('noOrdre')

@extend_schema(tags=['Ingredient'])
class IngredientCreateAPIView(generics.CreateAPIView):
    """
    Create tag
    """

    queryset = recette.models.Ingredient.objects.all()
    serializer_class = recette.serializer.IngredientSerializer

    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)  
    
@extend_schema(tags=['Ingredient'])
class IngredientUpdateAPIView(generics.UpdateAPIView):
    queryset = recette.models.Ingredient.objects.all()
    serializer_class = recette.serializer.IngredientSerializer

    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)    

    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)
    
    def update(self, request,  *args, **kwargs):
        return super().update(request, *args, **kwargs)
    
@extend_schema(tags=['Ingredient'])
class IngredientReorderAPIView(APIView):
    queryset = recette.models.Ingredient.objects.all()
    serializer_class = recette.serializer.ReorderPreparationSerializer

    def get_queryset(self):
        return recette.models.Ingredient.objects.filter(recette__id=self.kwargs["pk"]).order_by('noOrdre')
    
    def post(self, request, pk, pkIngredient, *args, **kwargs):
        try:
            serializer = self.serializer_class(data=request.data)
            serializer.is_valid(raise_exception=True)
            new_position = serializer.validated_data["newPosition"]

            with transaction.atomic():
                ingredient_to_move = recette.models.Ingredient.objects.get(id=self.kwargs["pkIngredient"])
               
                ingredients_to_reorder = recette.models.Ingredient.objects.filter(
                    recette_id=self.kwargs["pk"]
                ).exclude(id=ingredient_to_move.id).order_by('noOrdre')

                # On construit la nouvelle liste d'ingrédients
                new_ordered_list = []

                if new_position == 0:
                    new_ordered_list.append(ingredient_to_move)

                for i, ingredient in enumerate(ingredients_to_reorder):
                    new_ordered_list.append(ingredient)
                    if i + 1 == new_position:
                        new_ordered_list.append(ingredient_to_move)

                for index, ingredient in enumerate(new_ordered_list):
                    ingredient.noOrdre = index
                    ingredient.save()
                    
            serializer = recette.serializer.IngredientSerializer(new_ordered_list, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            print(e)
            return Response({"detail": f"Une erreur s'est produite lors de la réorganisation : {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR) 

@extend_schema(tags=['Ingredient'])
class IngredientDeleteAPIView(generics.DestroyAPIView):
    queryset = recette.models.Ingredient.objects.all()
    serializer_class = recette.serializer.IngredientSerializer

    def delete(self, request, pk, format=None):
        ingredient = self.get_object()
        ingredient.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

########################
########################

@extend_schema(tags=['Preparation'])
class PreparationRetrieveAPIView(generics.ListAPIView):
    """
    list of prépration
    """

    queryset = recette.models.Preparation.objects.all()
    serializer_class = recette.serializer.PreparationSerializer
    paginator = None
    
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.filter(recette_id=self.kwargs["pk"])
        return queryset.order_by('noOrdre')
    
@extend_schema(tags=['Preparation'])
class PreparationCreateAPIView(generics.CreateAPIView):
    """
    Create tag
    """

    queryset = recette.models.Preparation.objects.all()
    serializer_class = recette.serializer.PreparationSerializer

    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)  

@extend_schema(tags=['Preparation'])
class PreparationDeleteAPIView(generics.DestroyAPIView):
    queryset = recette.models.Preparation.objects.all()
    serializer_class = recette.serializer.PreparationSerializer

    def delete(self, request, pk, format=None):
        preparation = self.get_object()
        preparation.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)   

@extend_schema(tags=['Preparation'])
class PreparationUpdateAPIView(generics.UpdateAPIView):
    queryset = recette.models.Preparation.objects.all()
    serializer_class = recette.serializer.PreparationSerializer

    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)    

    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)
    
    def update(self, request,  *args, **kwargs):
        return super().update(request, *args, **kwargs)


    
@extend_schema(tags=['Preparation'])
class PreparationReorderAPIView(APIView):
    queryset = recette.models.Preparation.objects.all()
    serializer_class = recette.serializer.ReorderPreparationSerializer

    def get_queryset(self):
        return recette.models.Preparation.objects.filter(recette__id=self.kwargs["pk"]).order_by('noOrdre')
    
    def post(self, request, pk, pkPreparation, *args, **kwargs):
        try:
            serializer = self.serializer_class(data=request.data)
            serializer.is_valid(raise_exception=True)
            new_position = serializer.validated_data["newPosition"]

            with transaction.atomic():
                preparation_to_move = recette.models.Preparation.objects.get(id=self.kwargs["pkPreparation"])
               
                preparations_to_reorder = recette.models.Preparation.objects.filter(
                    recette_id=self.kwargs["pk"]
                ).exclude(id=preparation_to_move.id).order_by('noOrdre')

                new_ordered_list = []

                if new_position == 0:
                    new_ordered_list.append(preparation_to_move)

                for i, preparation in enumerate(preparations_to_reorder):
                    new_ordered_list.append(preparation)
                    if i + 1 == new_position:
                        new_ordered_list.append(preparation_to_move)

                for index, preparation in enumerate(new_ordered_list):
                    preparation.noOrdre = index
                    preparation.save()
                    
            serializer = recette.serializer.PreparationSerializer(new_ordered_list, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            print(e)
            return Response({"detail": f"Une erreur s'est produite lors de la réorganisation : {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR) 

############
###########
