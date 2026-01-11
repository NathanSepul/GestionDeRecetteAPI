from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from django.shortcuts import get_object_or_404

from recette.models import Recette
from tag.models import Tag
from tag.serializer import TagSerializer, TagRecetteLinkSerializer

@extend_schema(tags=['Tag'])
class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    pagination_class = None
    
    def get_queryset(self):
        """Filtre les tags par utilisateur et optionnellement par recetteId."""
        queryset = self.queryset.filter(user_id=self.request.user.id)
        recette_id = self.request.query_params.get('recetteId')

        if recette_id:
            queryset = queryset.filter(recettes__id=recette_id)
            
        return queryset.order_by('tag')

    def perform_create(self, serializer):
        """Assigne automatiquement l'utilisateur lors de la création."""
        serializer.save(user=self.request.user)


    # --- Actions Spécifiques pour les liens Recette <-> Tag ---

    @action(detail=False, methods=['get'], url_path='by_recette/(?P<idRecette>[^/.]+)')
    def list_by_recette(self, request, idRecette=None):
        """Récupère les tags d'une recette spécifique."""
        tags = Tag.objects.filter(
            recettes__id=idRecette, 
            user_id=request.user.id
        ).distinct()
        serializer = self.get_serializer(tags, many=True)
        return Response(serializer.data)


    @action(detail=False, methods=['post'], serializer_class=TagRecetteLinkSerializer)
    def link_recette(self, request):
        """Lie un tag à une recette."""
        serializer = TagRecetteLinkSerializer(data=request.data)
        if serializer.is_valid():
            recette = get_object_or_404(Recette, id=serializer.validated_data['recette_id'])
            tag = get_object_or_404(Tag, id=serializer.validated_data['tag_id'])
            
            tag.recettes.add(recette)
            return Response(status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    
    @action(detail=False, methods=['delete'], serializer_class=TagRecetteLinkSerializer)
    def unlink_recette(self, request):
        """Délie un tag d'une recette."""
        serializer = TagRecetteLinkSerializer(data=request.data)
        if serializer.is_valid():
            recette = get_object_or_404(Recette, id=serializer.validated_data['recette_id'])
            tag = get_object_or_404(Tag, id=serializer.validated_data['tag_id'])
            
            tag.recettes.remove(recette)
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)