from rest_framework import viewsets, status,permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema
from django.db import transaction
from django.db.models import Count, Max
from gestionDeRecette.api_views import IsOwner
from gestionDeRecette.utils import reorder
from typeRecette.models import TypeRecette
from typeRecette.serializer import TypeRecetteSerializer, ReorderTypeRecetteSerializer

@extend_schema(tags=['Type de recette'])
class TypeRecetteViewSet(viewsets.ModelViewSet):
    queryset = TypeRecette.objects.all()
    serializer_class = TypeRecetteSerializer
    pagination_class = None
    permission_classes = [permissions.IsAuthenticated, IsOwner]
    
    def get_queryset(self):
        """
        Return the list of type recette
        """
        queryset = super().get_queryset()
        
        # queryset = queryset.filter(user_id=self.request.user.id)
        userID = self.request.GET.get('userId')
        if userID:
            queryset = queryset.filter(user_id=userID)
        
        return queryset.annotate(recipe_count=Count('recette')).order_by('noOrdre')
    
    def perform_create(self, serializer):
        """Assigne automatiquement l'utilisateur lors de la création."""
        max_no_ordre = TypeRecette.objects.filter(  user=self.request.user ).aggregate(Max('noOrdre'))['noOrdre__max']
        next_no_ordre = (max_no_ordre if max_no_ordre is not None else -1) + 1
        serializer.save(user=self.request.user, noOrdre=next_no_ordre)

    @action(detail=True, methods=['post'], serializer_class=ReorderTypeRecetteSerializer)
    def reorder(self, request, pk=None):
        """Triage de l'ordre des types de recettes."""
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            type_to_move = self.get_object()
            # annotate : TypeRecetteSerializer lit recipe_count sur chaque type renvoyé
            siblings = TypeRecette.objects.filter(user_id=self.request.user.id).annotate(recipe_count=Count('recette'))
            new_ordered_list = reorder(type_to_move, siblings, serializer.validated_data["newPosition"])

        serializer = TypeRecetteSerializer(new_ordered_list, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)