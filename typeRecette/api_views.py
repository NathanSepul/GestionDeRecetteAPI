from rest_framework import generics
import typeRecette
import typeRecette.serializer
import typeRecette.models
from rest_framework.response import Response
from rest_framework import status

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

class TypeRecetteCreateAPIView(generics.CreateAPIView):
    """
    Create type recette
    """

    queryset = typeRecette.models.TypeRecette.objects.all()
    serializer_class = typeRecette.serializer.TypeRecetteSerializer
    paginator = None    
    
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

class TypeRecetteUpdateAPIView(generics.UpdateAPIView):
    queryset = typeRecette.models.TypeRecette.objects.all()
    serializer_class = typeRecette.serializer.TypeRecetteSerializer

    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)    

    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)
    
    def update(self, request,  *args, **kwargs):
        return super().update(request, *args, **kwargs)

class TypeRecetteDeleteAPIView(generics.DestroyAPIView):
    queryset = typeRecette.models.TypeRecette.objects.all()
    serializer_class = typeRecette.serializer.TypeRecetteSerializer

    def delete(self, request, pk, format=None):
        print("kkkkk")
        typeRecette = self.get_object()
        typeRecette.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)  