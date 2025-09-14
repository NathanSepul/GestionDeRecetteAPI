from rest_framework import generics, permissions
from recette.models import Recette
import tag
from tag.models import Tag
import tag.serializer
from rest_framework.response import Response
from rest_framework import status
from drf_spectacular.utils import extend_schema
from rest_framework.views import APIView 

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
        queryset = queryset.filter(user_id=self.request.user.id)
        queryparam_Recette = self.request.GET.get('recetteId', '')

        if queryparam_Recette:
            queryset = queryset.filter(recettes=queryparam_Recette)
            
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

@extend_schema(tags=['Tag'])
class TagRecetteListAPIView(generics.ListAPIView):
    """
    list of tags
    """

    queryset = tag.models.Tag.objects.all()
    serializer_class = tag.serializer.TagSerializer
    paginator = None

    def get_queryset(self):
        idRecette = self.kwargs.get('idRecette')
        if not idRecette:
            raise Response(status=status.HTTP_400_BAD_REQUEST)   
        return Tag.objects.filter(recettes__id=idRecette).filter(user_id=self.request.user.id).distinct()


class TagRecetteCreateAPIView(APIView):
    def post(self, request):
        serializer = tag.serializer.TagRecetteLinkSerializer(data=request.data)
        if serializer.is_valid():
            recette_id = serializer.validated_data['recette_id']
            tag_id = serializer.validated_data['tag_id']

            recette = Recette.objects.get(id=recette_id)
            tagToLink = Tag.objects.get(id=tag_id)

            tagToLink.recettes.add(recette) 

            return Response(status=status.HTTP_201_CREATED)   

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class TagRecetteDeleteAPIView(generics.DestroyAPIView):
    def delete(self, request):
        serializer = tag.serializer.TagRecetteLinkSerializer(data=request.data)
        
        if serializer.is_valid():
            recette_id = serializer.validated_data['recette_id']
            tag_id = serializer.validated_data['tag_id']

            recette = Recette.objects.get(id=recette_id)
            tagToRemove = Tag.objects.get(id=tag_id)
            tagToRemove.recettes.remove(recette)

            return Response(status=status.HTTP_204_NO_CONTENT)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)