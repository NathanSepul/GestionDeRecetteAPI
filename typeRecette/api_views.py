from rest_framework import generics
import typeRecette
import typeRecette.serializer
import typeRecette.models
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema
from rest_framework.views import APIView 
from django.db import transaction

@extend_schema(tags=['Type de recette'])
class TypeRecetteListAPIView(generics.ListAPIView):
    """
    list of type recette
    """

    queryset = typeRecette.models.TypeRecette.objects.all()
    serializer_class = typeRecette.serializer.TypeRecetteSerializer
    paginator = None

    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    def get_queryset(self):
        """
        Return the list of type recette
        """
        queryset = super().get_queryset()

        return queryset.order_by('noOrdre')

@extend_schema(tags=['Type de recette'])
class TypeRecetteCreateAPIView(generics.CreateAPIView):
    """
    Create type recette
    """

    queryset = typeRecette.models.TypeRecette.objects.all()
    serializer_class = typeRecette.serializer.TypeRecetteSerializer
    paginator = None    
    
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

@extend_schema(tags=['Type de recette'])
class TypeRecetteUpdateAPIView(generics.UpdateAPIView):
    queryset = typeRecette.models.TypeRecette.objects.all()
    serializer_class = typeRecette.serializer.TypeRecetteSerializer

    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)    

    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)
    
    def update(self, request,  *args, **kwargs):
        return super().update(request, *args, **kwargs)

@extend_schema(tags=['Type de recette'])
class TypeRecetteDeleteAPIView(generics.DestroyAPIView):
    queryset = typeRecette.models.TypeRecette.objects.all()
    serializer_class = typeRecette.serializer.TypeRecetteSerializer

    def delete(self, request, pk, format=None):
        typeRecette = self.get_object()
        typeRecette.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)  


@extend_schema(tags=['Type de recette'])
class TypeRecetteReorderAPIView(APIView):
    queryset = typeRecette.models.TypeRecette.objects.all()
    serializer_class = typeRecette.serializer.ReorderTypeRecetteSerializer

    def post(self, request, pk, *args, **kwargs):
        try:
            serializer = self.serializer_class(data=request.data)
            serializer.is_valid(raise_exception=True)
            new_position = serializer.validated_data["newPosition"]

            with transaction.atomic():
                type_to_move = typeRecette.models.TypeRecette.objects.get(id=self.kwargs["pk"])
                type_to_reorder = typeRecette.models.TypeRecette.objects.exclude(id=type_to_move.id).order_by('noOrdre')

                new_ordered_list = []

                if new_position == 0:
                    new_ordered_list.append(type_to_move)

                for i, type in enumerate(type_to_reorder):
                    new_ordered_list.append(type)
                    if i + 1 == new_position:
                        new_ordered_list.append(type_to_move)

                for index, type in enumerate(new_ordered_list):
                    type.noOrdre = index
                    type.save()
                    
            serializer =  typeRecette.serializer.TypeRecetteSerializer(new_ordered_list, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"detail": f"Une erreur s'est produite lors de la réorganisation : {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR) 
