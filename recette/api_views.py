from decimal import Decimal
from rest_framework import generics
from rest_framework.response import Response
from rest_framework import status
import recette
import recette.models
import recette.serializer




######
######

class RecetteListAPIView(generics.ListAPIView):
    """
    list of recette
    """

    queryset = recette.models.Recette.objects.all()
    serializer_class = recette.serializer.RecetteSerializer

    # @swagger_auto_schema(operation_id='Get comments', security=[],)
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    def get_queryset(self):
        queryset = super().get_queryset()

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
                    for tag_id in tag_ids:
                        queryset = queryset.filter(tagrecette__tag__id=tag_id)
                    
                    queryset = queryset.distinct()
                else:
                    pass 

            except ValueError:
                from rest_framework.exceptions import ValidationError
                raise ValidationError({"tags": "Les IDs de tags doivent être des entiers séparés par des virgules."})

        if queryparam_OrderBy:
            return queryset.order_by(queryparam_OrderBy)
        else:
            return queryset.order_by('titre')
        

class RecetteRetrieveAPIView(generics.RetrieveAPIView):
    """
    Returns the **selected** Recette informations.
    """

    queryset = recette.models.Recette.objects.all()
    serializer_class = recette.serializer.RecetteSerializer

    # @swagger_auto_schema(operation_id='Get recette by id', security=[],)
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    

class RecetteCreateAPIView(generics.CreateAPIView):
    """
    Create tag
    """

    queryset = recette.models.Recette.objects.all()
    serializer_class = recette.serializer.RecetteSerializer

    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)    

class RecetteDeleteAPIView(generics.DestroyAPIView):
    queryset = recette.models.Recette.objects.all()
    serializer_class = recette.serializer.RecetteSerializer

    def delete(self, request, pk, format=None):
        recette = self.get_object()
        recette.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
class RecetteUpdateAPIView(generics.UpdateAPIView):
    queryset = recette.models.Recette.objects.all()
    serializer_class = recette.serializer.RecetteSerializer

    def _adapt_ingredient_quantities(self, recette_instance, scaling_factor):
        for ingredient in recette_instance.ingredients.all():
            if ingredient.quantite is not None and not ingredient.isSection:
                new_quantity = ingredient.quantite * scaling_factor
                ingredient.quantite = new_quantity.quantize(Decimal('0.01')) # Round to 2 decimal places
                ingredient.save() # Save the updated ingredient

    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)    

    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)
    
    def update(self, request,  *args, **kwargs):
        try:
            instance = self.get_object()
            old_portion = instance.portion
            
            response = super().update(request, *args, **kwargs)
                
            if request.data["image"] is None:
                instance.image = None
            else: 
                instance.image= request.data["image"]

            if response.status_code == status.HTTP_200_OK:    
                new_portion = Decimal(request.data["portion"])
                if old_portion != 0: 
                    scaling_factor = new_portion / old_portion 
                    print(scaling_factor)     
                    self._adapt_ingredient_quantities(instance, scaling_factor)


            instance.typeRecette__id = request.data["typeRecette"]; 
            instance.portion = new_portion; 
            instance.titre = request.data["titre"]; 
            instance.save()
            return Response("Recette updated", status=status.HTTP_200_OK)
        except Exception as e:
            raise Response(f"An error occurred during update recette: {e}")
                
########################
########################


class InredientRetrieveAPIView(generics.ListAPIView):
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
        return queryset.order_by('recette_id')
    
class InredientCreateAPIView(generics.CreateAPIView):
    """
    Create tag
    """

    queryset = recette.models.Ingredient.objects.all()
    serializer_class = recette.serializer.IngredientSerializer

    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)  

class InredientUpdateAPIView(generics.UpdateAPIView):
    queryset = recette.models.Ingredient.objects.all()
    serializer_class = recette.serializer.IngredientSerializer

    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)    

    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)
    
    def update(self, request,  *args, **kwargs):
        return super().update(request, *args, **kwargs)

class IngredientDeleteAPIView(generics.DestroyAPIView):
    queryset = recette.models.Ingredient.objects.all()
    serializer_class = recette.serializer.IngredientSerializer

    def delete(self, request, pk, format=None):
        ingredient = self.get_object()
        ingredient.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

########################
########################


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

class PreparationCreateAPIView(generics.CreateAPIView):
    """
    Create tag
    """

    queryset = recette.models.Preparation.objects.all()
    serializer_class = recette.serializer.PreparationSerializer

    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)  

class PreparationDeleteAPIView(generics.DestroyAPIView):
    queryset = recette.models.Preparation.objects.all()
    serializer_class = recette.serializer.PreparationSerializer

    def delete(self, request, pk, format=None):
        preparation = self.get_object()
        preparation.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)   

class PreparationUpdateAPIView(generics.UpdateAPIView):
    queryset = recette.models.Preparation.objects.all()
    serializer_class = recette.serializer.PreparationSerializer

    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)    

    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)
    
    def update(self, request,  *args, **kwargs):
        return super().update(request, *args, **kwargs)
############
###########
