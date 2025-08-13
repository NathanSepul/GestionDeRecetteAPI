from rest_framework import generics
import tag
import tag.serializer
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema

@extend_schema(tags=['Tag'])
class TagListAPIView(generics.ListAPIView):
    """
    list of tags
    """

    queryset = tag.models.Tag.objects.all()
    serializer_class = tag.serializer.TagSerializer
    paginator = None
    
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
    
    def get_queryset(self):
        queryset = super().get_queryset()
        queryparam_Recette = self.request.GET.get('recetteId', '')

        if queryparam_Recette:
            queryset = queryset.filter(tagrecette__recette=queryparam_Recette)
            
        return queryset.order_by('tag')

@extend_schema(tags=['Tag'])
class TagCreateAPIView(generics.CreateAPIView):
    """
    Create tag
    """

    queryset = tag.models.Tag.objects.all()
    serializer_class = tag.serializer.TagSerializer

    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

class TagUpdateAPIView(generics.UpdateAPIView):
    queryset = tag.models.Tag.objects.all()
    serializer_class = tag.serializer.TagSerializer

    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)    

    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)
    
    def update(self, request,  *args, **kwargs):
        return super().update(request, *args, **kwargs)

@extend_schema(tags=['Tag'])  
class TagDeleteAPIView(generics.DestroyAPIView):
    queryset = tag.models.Tag.objects.all()
    serializer_class = tag.serializer.TagSerializer

    def delete(self, request, pk, format=None):
        tag = self.get_object()
        tag.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)   
    

########################
########################


# class TagRecetteCreateAPIView(generics.CreateAPIView):
#     """
#     Create tag
#     """

#     queryset = tag.models.TagRecette.objects.all()
#     serializer_class = tag.serializer.TagRecetteSerializer

#     def post(self, request, *args, **kwargs):
#         return super().post(request, *args, **kwargs)

# class TagRecetteDeleteAPIView(generics.DestroyAPIView):
#     queryset = tag.models.TagRecette.objects.all()
#     serializer_class = tag.serializer.TagRecetteSerializer

#     def delete(self, request, pk, format=None):
#         tagReceette = self.get_object()
#         tagReceette.delete()
#         return Response(status=status.HTTP_204_NO_CONTENT)  

# class TagRecetteUpdateAPIView(generics.UpdateAPIView):
#     queryset = tag.models.TagRecette.objects.all()
#     serializer_class = tag.serializer.TagRecetteSerializer

#     def post(self, request, *args, **kwargs):
#         return super().post(request, *args, **kwargs)    

#     def put(self, request, *args, **kwargs):
#         return super().put(request, *args, **kwargs)
    
#     def update(self, request,  *args, **kwargs):
#         return super().update(request, *args, **kwargs)